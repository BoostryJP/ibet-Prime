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

import hashlib
from datetime import UTC, datetime
from unittest import mock
from unittest.mock import ANY, MagicMock

import pytest
from sqlalchemy import select

import config
from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain.tx_params.ibet_security_token_escrow import (
    ApproveTransferParams as EscrowApproveTransferParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    ApproveTransferParams,
    CancelTransferParams,
)
from app.model.db import (
    Account,
    AuthToken,
    IDXPersonalInfo,
    IDXTransferApproval,
    PersonalInfoDataSource,
    Token,
    TokenType,
    TokenVersion,
    TransferApprovalHistory,
    TransferApprovalOperationType,
)
from app.utils.e2ee_utils import E2EEUtils
from tests.account_config import config_eth_account


class TestUpdateBondTokenTransferApprovalStatus:
    # target API endpoint
    base_url = "/bond/transfer_approvals/{}/{}"

    test_transaction_hash = "test_transaction_hash"

    test_token_address = "test_token_address"
    test_exchange_address = "0x1234567890aBcDFE1234567890abcDFE12345679"
    test_from_address = "test_from_address"
    test_to_address = "test_to_address"
    test_application_datetime = datetime(year=2019, month=9, day=1)
    test_application_blocktimestamp = datetime(year=2019, month=9, day=2)
    test_approval_datetime = datetime(year=2019, month=9, day=3)
    test_approval_blocktimestamp = datetime(year=2019, month=9, day=4)
    test_cancellation_blocktimestamp = datetime(year=2019, month=9, day=5)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # APPROVE
    # token
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "application_id": 100,
            "data": str(datetime.now(UTC).replace(tzinfo=None).timestamp()),
        }

        mock_transfer.assert_called_once_with(
            data=ApproveTransferParams(**_expected),
            tx_from=issuer_address,
            private_key=ANY,
        )

        approval_op_list: list[TransferApprovalHistory] = db.scalars(
            select(TransferApprovalHistory)
        ).all()
        assert len(approval_op_list) == 1
        approval_op = approval_op_list[0]
        assert approval_op.token_address == self.test_token_address
        assert approval_op.exchange_address == config.ZERO_ADDRESS
        assert approval_op.application_id == 100
        assert approval_op.operation_type == TransferApprovalOperationType.APPROVE.value
        assert approval_op.from_address_personal_info == {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert approval_op.to_address_personal_info == {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }

    # <Normal_1_2>
    # APPROVE
    # exchange
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
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
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        # mock
        IbetSecurityTokenEscrow_approve_transfer = mock.patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        db.commit()

        # request target API
        with IbetSecurityTokenEscrow_approve_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "escrow_id": 100,
            "data": str(datetime.now(UTC).replace(tzinfo=None).timestamp()),
        }

        mock_transfer.assert_called_once_with(
            data=EscrowApproveTransferParams(**_expected),
            tx_from=issuer_address,
            private_key=ANY,
        )

        approval_op_list: list[TransferApprovalHistory] = db.scalars(
            select(TransferApprovalHistory)
        ).all()
        assert len(approval_op_list) == 1
        approval_op = approval_op_list[0]
        assert approval_op.token_address == self.test_token_address
        assert approval_op.exchange_address == self.test_exchange_address
        assert approval_op.application_id == 100
        assert approval_op.operation_type == TransferApprovalOperationType.APPROVE.value
        assert approval_op.from_address_personal_info == {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert approval_op.to_address_personal_info == {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }

    # <Normal_2_1>
    # CANCEL
    # token
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with IbetSecurityTokenContract_cancel_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
                json={"operation_type": "cancel"},
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "application_id": 100,
            "data": str(datetime.now(UTC).replace(tzinfo=None).timestamp()),
        }

        mock_transfer.assert_called_once_with(
            data=CancelTransferParams(**_expected),
            tx_from=issuer_address,
            private_key=ANY,
        )

        cancel_op_list: list[TransferApprovalHistory] = db.scalars(
            select(TransferApprovalHistory)
        ).all()
        assert len(cancel_op_list) == 1
        cancel_op = cancel_op_list[0]
        assert cancel_op.token_address == self.test_token_address
        assert cancel_op.exchange_address == config.ZERO_ADDRESS
        assert cancel_op.application_id == 100
        assert cancel_op.operation_type == TransferApprovalOperationType.CANCEL.value
        assert cancel_op.from_address_personal_info == {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        assert cancel_op.to_address_personal_info == {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }

    # <Normal_3>
    # Authorization by auth-token
    @pytest.mark.freeze_time("2021-04-27 12:34:56")
    def test_normal_3(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        auth_token = AuthToken()
        auth_token.issuer_address = issuer_address
        auth_token.auth_token = hashlib.sha256("test_auth_token".encode()).hexdigest()
        auth_token.valid_duration = 0
        db.add(auth_token)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "auth-token": "test_auth_token",
                },
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json() is None

        _expected = {
            "application_id": 100,
            "data": str(datetime.now(UTC).replace(tzinfo=None).timestamp()),
        }

        mock_transfer.assert_called_once_with(
            data=ApproveTransferParams(**_expected),
            tx_from=issuer_address,
            private_key=ANY,
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
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": None,
                    "loc": ["header", "issuer-address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["body"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
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
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": {},
                    "loc": ["body", "operation_type"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
        }

    # <Error_1_3>
    # Validation Error
    # invalid value: body
    def test_error_1_3(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "test"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "ctx": {"expected": "'approve' or 'cancel'"},
                    "input": "test",
                    "loc": ["body", "operation_type"],
                    "msg": "Input should be 'approve' or 'cancel'",
                    "type": "enum",
                }
            ],
        }

    # <Error_1_4>
    # Validation Error
    # invalid value: header
    def test_error_1_4(self, client, db):
        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={"issuer-address": "issuer_address", "eoa-password": "password"},
        )

        # assertion
        assert resp.status_code == 422
        assert resp.json() == {
            "meta": {"code": 1, "title": "RequestValidationError"},
            "detail": [
                {
                    "input": "issuer_address",
                    "loc": ["header", "issuer-address"],
                    "msg": "issuer-address is not a valid address",
                    "type": "value_error",
                },
                {
                    "input": "password",
                    "loc": ["header", "eoa-password"],
                    "msg": "eoa-password is not a Base64-encoded encrypted data",
                    "type": "value_error",
                },
            ],
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
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
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

        db.commit()

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password_test"),
            },
        )

        # assertion
        assert resp.status_code == 401
        assert resp.json() == {
            "meta": {"code": 1, "title": "AuthorizationError"},
            "detail": "issuer does not exist, or password mismatch",
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

        db.commit()

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "token not found",
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json() == {
            "meta": {"code": 1, "title": "NotFound"},
            "detail": "transfer approval not found",
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.token_status = 0
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        db.commit()

        id = 10

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "this token is temporarily unavailable",
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = self.test_approval_datetime
        _idx_transfer_approval.approval_blocktimestamp = (
            self.test_approval_blocktimestamp
        )
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = True
        db.add(_idx_transfer_approval)

        db.commit()

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "already approved",
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = (
            self.test_cancellation_blocktimestamp
        )
        _idx_transfer_approval.cancelled = True
        _idx_transfer_approval.escrow_finished = None
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        db.commit()

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "canceled application",
        }

    # <Error_4_4>
    # Invalid Parameter Error
    # escrow has not been finished yet
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
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
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.escrow_finished = False
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        db.commit()

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
            json={"operation_type": "cancel"},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "escrow has not been finished yet",
        }

    # <Error_4_5>
    # Invalid Parameter Error
    # application that cannot be canceled
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
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
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.escrow_finished = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        db.commit()

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
            json={"operation_type": "cancel"},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "application that cannot be canceled",
        }

    # <Error_4_6>
    # Invalid Parameter Error
    # This operation is duplicated
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = False
        _idx_transfer_approval.escrow_finished = True
        _idx_transfer_approval.transfer_approved = None
        db.add(_idx_transfer_approval)

        _cancel_op = TransferApprovalHistory()
        _cancel_op.token_address = self.test_token_address
        _cancel_op.exchange_address = config.ZERO_ADDRESS
        _cancel_op.application_id = 100
        _cancel_op.operation_type = TransferApprovalOperationType.CANCEL.value
        db.add(_cancel_op)

        db.commit()

        # request target api
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
            json={"operation_type": "cancel"},
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 1, "title": "InvalidParameterError"},
            "detail": "duplicate operation",
        }

    # <Error_5_1>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenInterface.approve_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
        MagicMock(side_effect=SendTransactionError()),
    )
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }

    # <Error_5_2>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenInterface.approve_transfer
    # return fail with Revert
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            side_effect=ContractRevertError("120902"),
        )
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with (
            IbetSecurityTokenContract_approve_transfer,
            IbetSecurityTokenContract_cancel_transfer,
        ):
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 120902, "title": "ContractRevertError"},
            "detail": "Application is invalid.",
        }

    # <Error_5_3>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenEscrow.approve_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
        MagicMock(side_effect=SendTransactionError()),
    )
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
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
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            json={"operation_type": "approve"},
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }

    # <Error_5_4>
    # APPROVE
    # Send Transaction Error
    # IbetSecurityTokenEscrow.approve_transfer
    # return fail with Revert
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
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
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        _idx_transfer_approval.escrow_finished = True
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenEscrow_approve_transfer = mock.patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            side_effect=ContractRevertError("120902"),
        )

        # request target API
        with IbetSecurityTokenEscrow_approve_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 120902, "title": "ContractRevertError"},
            "detail": "Application is invalid.",
        }

    # <Error_6_1>
    # CANCEL
    # Send Transaction Error
    # IbetSecurityTokenInterface.cancel_transfer
    # raise SendTransactionError
    @mock.patch(
        "app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
        MagicMock(side_effect=SendTransactionError()),
    )
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # request target API
        resp = client.post(
            self.base_url.format(self.test_token_address, id),
            headers={
                "issuer-address": issuer_address,
                "eoa-password": E2EEUtils.encrypt("password"),
            },
            json={"operation_type": "cancel"},
        )

        # assertion
        assert resp.status_code == 503
        assert resp.json() == {
            "meta": {"code": 2, "title": "SendTransactionError"},
            "detail": "failed to send transaction",
        }

    # <Error_6_2>
    # CANCEL
    # Send Transaction Error
    # IbetSecurityTokenInterface.cancel_transfer
    # return fail with Revert
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
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        _personal_info_to = IDXPersonalInfo()
        _personal_info_to.account_address = self.test_to_address
        _personal_info_to.issuer_address = issuer_address
        _personal_info_to._personal_info = {
            "key_manager": "key_manager_test2",
            "name": "name_test2",
            "postal_code": "postal_code_test2",
            "address": "address_test2",
            "email": "email_test2",
            "birth": "birth_test2",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_to.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_to)

        db.commit()

        # mock
        IbetSecurityTokenContract_cancel_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
            side_effect=ContractRevertError("120802"),
        )

        # request target API
        with IbetSecurityTokenContract_cancel_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
                json={"operation_type": "cancel"},
            )

        # assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 120802, "title": "ContractRevertError"},
            "detail": "Application is invalid.",
        }

    # <Error_7_1>
    # InvalidParameterError
    # personal information for from_address is not registered
    def test_error_7_1(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 101, "title": "OperationNotAllowedStateError"},
            "detail": "personal information for from_address is not registered",
        }

    # <Error_7_2>
    # InvalidParameterError
    # personal information for to_address is not registered
    def test_error_7_2(self, client, db):
        issuer = config_eth_account("user1")
        issuer_address = issuer["address"]

        # prepare data
        account = Account()
        account.issuer_address = issuer_address
        account.keyfile = issuer["keyfile_json"]
        account.eoa_password = E2EEUtils.encrypt("password")
        db.add(account)

        _token = Token()
        _token.type = TokenType.IBET_STRAIGHT_BOND.value
        _token.tx_hash = self.test_transaction_hash
        _token.issuer_address = issuer_address
        _token.token_address = self.test_token_address
        _token.abi = {}
        _token.version = TokenVersion.V_24_09
        db.add(_token)

        id = 10
        _idx_transfer_approval = IDXTransferApproval()
        _idx_transfer_approval.id = id
        _idx_transfer_approval.token_address = self.test_token_address
        _idx_transfer_approval.exchange_address = config.ZERO_ADDRESS
        _idx_transfer_approval.application_id = 100
        _idx_transfer_approval.from_address = self.test_from_address
        _idx_transfer_approval.to_address = self.test_to_address
        _idx_transfer_approval.amount = 200
        _idx_transfer_approval.application_datetime = self.test_application_datetime
        _idx_transfer_approval.application_blocktimestamp = (
            self.test_application_blocktimestamp
        )
        _idx_transfer_approval.approval_datetime = None
        _idx_transfer_approval.approval_blocktimestamp = None
        _idx_transfer_approval.cancellation_blocktimestamp = None
        _idx_transfer_approval.cancelled = None
        db.add(_idx_transfer_approval)

        _personal_info_from = IDXPersonalInfo()
        _personal_info_from.account_address = self.test_from_address
        _personal_info_from.issuer_address = issuer_address
        _personal_info_from._personal_info = {
            "key_manager": "key_manager_test1",
            "name": "name_test1",
            "postal_code": "postal_code_test1",
            "address": "address_test1",
            "email": "email_test1",
            "birth": "birth_test1",
            "is_corporate": False,
            "tax_category": 10,
        }
        _personal_info_from.data_source = PersonalInfoDataSource.ON_CHAIN
        db.add(_personal_info_from)

        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = mock.patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1}),
        )

        # request target API
        with IbetSecurityTokenContract_approve_transfer:
            resp = client.post(
                self.base_url.format(self.test_token_address, id),
                json={"operation_type": "approve"},
                headers={
                    "issuer-address": issuer_address,
                    "eoa-password": E2EEUtils.encrypt("password"),
                },
            )

        # Assertion
        assert resp.status_code == 400
        assert resp.json() == {
            "meta": {"code": 101, "title": "OperationNotAllowedStateError"},
            "detail": "personal information for to_address is not registered",
        }
