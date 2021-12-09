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
import datetime

import pytest
from unittest.mock import (
    patch,
    ANY
)

from app.model.db import (
    Account,
    IDXTransferApproval,
    Token,
    TokenType,
    AdditionalTokenInfo,
    TransferApprovalHistory,
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.schema.token import (
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenCancelTransfer,
    IbetSecurityTokenEscrowApproveTransfer
)
from app.exceptions import SendTransactionError
from batch.processor_auto_transfer_approval import (
    Sinks,
    DBSink,
    Processor
)

from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db):
    _sink = Sinks()
    _sink.register(DBSink(db))
    return Processor(sink=_sink, db=db)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1_1>
    # tx_receipt status is 1 (Success)
    # Apply from IbetStraightBond
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1_1(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : Token (issuer does not exist)
        dummy_issuer_token = Token()
        dummy_issuer_token.type = TokenType.IBET_STRAIGHT_BOND
        dummy_issuer_token.token_address = "dummy_issuer_token_address"
        dummy_issuer_token.issuer_address = "ISSUER_DUMMY_ADDRESS"
        dummy_issuer_token.abi = "abi"
        dummy_issuer_token.tx_hash = "tx_hash"
        db.add(dummy_issuer_token)

        # Prepare data : Token (manually approval)
        manual_token = Token()
        manual_token.type = TokenType.IBET_STRAIGHT_BOND
        manual_token.token_address = "manual_token_address"
        manual_token.issuer_address = _account
        manual_token.abi = "abi"
        manual_token.tx_hash = "tx_hash"
        db.add(manual_token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval_0 = IDXTransferApproval()
        idx_transfer_approval_0.token_address = "token_address"
        idx_transfer_approval_0.application_id = 0
        idx_transfer_approval_0.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_0)

        # Prepare data : IDXTransferApproval, TransferApprovalHistory(approved)
        idx_transfer_approval_1 = IDXTransferApproval()
        idx_transfer_approval_1.token_address = "token_address"
        idx_transfer_approval_1.application_id = 1
        idx_transfer_approval_1.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_1)

        transfer_approval_history = TransferApprovalHistory()
        transfer_approval_history.token_address = "token_address"
        transfer_approval_history.application_id = 1
        transfer_approval_history.result = 2
        db.add(transfer_approval_history)

        # Prepare data : IDXTransferApproval(cancelled)
        idx_transfer_approval_2 = IDXTransferApproval()
        idx_transfer_approval_2.token_address = "token_address"
        idx_transfer_approval_2.application_id = 2
        idx_transfer_approval_2.application_blocktimestamp = datetime.datetime.utcnow()
        idx_transfer_approval_2.cancelled = True
        db.add(idx_transfer_approval_2)

        # Prepare data : IDXTransferApproval(Token does not exists)
        idx_transfer_approval_4 = IDXTransferApproval()
        idx_transfer_approval_4.token_address = "dummy_token_address"
        idx_transfer_approval_4.application_id = 0
        idx_transfer_approval_4.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_4)
        db.commit()

        # Prepare data : IDXTransferApproval(manually approval)
        idx_transfer_approval_5 = IDXTransferApproval()
        idx_transfer_approval_5.token_address = "manual_token_address"
        idx_transfer_approval_5.application_id = 0
        idx_transfer_approval_5.application_blocktimestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(idx_transfer_approval_5)
        db.commit()

        # Prepare data : AdditionalTokenInfo(manually approval)
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = "manual_token_address"
        additional_token_info_1.is_manual_transfer_approval = None
        additional_token_info_1.block_number = 1
        additional_token_info_1.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 0)
        db.add(additional_token_info_1)
        additional_token_info_2 = AdditionalTokenInfo()
        additional_token_info_2.token_address = "manual_token_address"
        additional_token_info_2.is_manual_transfer_approval = False
        additional_token_info_2.block_number = 2
        additional_token_info_2.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 1)
        db.add(additional_token_info_2)
        additional_token_info_3 = AdditionalTokenInfo()
        additional_token_info_3.token_address = "manual_token_address"
        additional_token_info_3.is_manual_transfer_approval = True
        additional_token_info_3.block_number = 3
        additional_token_info_3.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(additional_token_info_3)
        additional_token_info_4 = AdditionalTokenInfo()
        additional_token_info_4.token_address = "manual_token_address"
        additional_token_info_4.is_manual_transfer_approval = False
        additional_token_info_4.block_number = 4
        additional_token_info_4.block_timestamp = datetime.datetime(2020, 1, 1, 13, 0, 0)
        db.add(additional_token_info_4)
        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            # Execute batch
            processor.process()

        # Assertion : Success
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history.result == 1

        # Assertion : Skipped (approved)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 1). \
            first()
        assert transfer_approval_history.result == 2

        # Assertion : Skipped (cancelled)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 2). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token issuer does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_issuer_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (manually approval)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "manual_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        _expected = {
            "application_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address="token_address",
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )

    # <Normal_1_2>
    # tx_receipt status is 1 (Success)
    # Apply from IbetShare
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1_2(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : Token (issuer does not exist)
        dummy_issuer_token = Token()
        dummy_issuer_token.type = TokenType.IBET_SHARE
        dummy_issuer_token.token_address = "dummy_issuer_token_address"
        dummy_issuer_token.issuer_address = "ISSUER_DUMMY_ADDRESS"
        dummy_issuer_token.abi = "abi"
        dummy_issuer_token.tx_hash = "tx_hash"
        db.add(dummy_issuer_token)

        # Prepare data : Token (manually approval)
        manual_token = Token()
        manual_token.type = TokenType.IBET_STRAIGHT_BOND
        manual_token.token_address = "manual_token_address"
        manual_token.issuer_address = _account
        manual_token.abi = "abi"
        manual_token.tx_hash = "tx_hash"
        db.add(manual_token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval_0 = IDXTransferApproval()
        idx_transfer_approval_0.token_address = "token_address"
        idx_transfer_approval_0.application_id = 0
        idx_transfer_approval_0.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_0)

        # Prepare data : IDXTransferApproval, TransferApprovalHistory(approved)
        idx_transfer_approval_1 = IDXTransferApproval()
        idx_transfer_approval_1.token_address = "token_address"
        idx_transfer_approval_1.application_id = 1
        idx_transfer_approval_1.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_1)

        transfer_approval_history = TransferApprovalHistory()
        transfer_approval_history.token_address = "token_address"
        transfer_approval_history.application_id = 1
        transfer_approval_history.result = 2
        db.add(transfer_approval_history)

        # Prepare data : IDXTransferApproval(cancelled)
        idx_transfer_approval_2 = IDXTransferApproval()
        idx_transfer_approval_2.token_address = "token_address"
        idx_transfer_approval_2.application_id = 2
        idx_transfer_approval_2.application_blocktimestamp = datetime.datetime.utcnow()
        idx_transfer_approval_2.cancelled = True
        db.add(idx_transfer_approval_2)

        # Prepare data : IDXTransferApproval(Token does not exists)
        idx_transfer_approval_4 = IDXTransferApproval()
        idx_transfer_approval_4.token_address = "dummy_token_address"
        idx_transfer_approval_4.application_id = 0
        idx_transfer_approval_4.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_4)
        db.commit()

        # Prepare data : IDXTransferApproval(manually approval)
        idx_transfer_approval_5 = IDXTransferApproval()
        idx_transfer_approval_5.token_address = "manual_token_address"
        idx_transfer_approval_5.application_id = 0
        idx_transfer_approval_5.application_blocktimestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(idx_transfer_approval_5)
        db.commit()

        # Prepare data : AdditionalTokenInfo(manually approval)
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = "manual_token_address"
        additional_token_info_1.is_manual_transfer_approval = None
        additional_token_info_1.block_number = 1
        additional_token_info_1.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 0)
        db.add(additional_token_info_1)
        additional_token_info_2 = AdditionalTokenInfo()
        additional_token_info_2.token_address = "manual_token_address"
        additional_token_info_2.is_manual_transfer_approval = False
        additional_token_info_2.block_number = 2
        additional_token_info_2.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 1)
        db.add(additional_token_info_2)
        additional_token_info_3 = AdditionalTokenInfo()
        additional_token_info_3.token_address = "manual_token_address"
        additional_token_info_3.is_manual_transfer_approval = True
        additional_token_info_3.block_number = 3
        additional_token_info_3.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(additional_token_info_3)
        additional_token_info_4 = AdditionalTokenInfo()
        additional_token_info_4.token_address = "manual_token_address"
        additional_token_info_4.is_manual_transfer_approval = False
        additional_token_info_4.block_number = 4
        additional_token_info_4.block_timestamp = datetime.datetime(2020, 1, 1, 13, 0, 0)
        db.add(additional_token_info_4)
        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            # Execute batch
            processor.process()

        # Assertion : Success
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history.exchange_address is None
        assert transfer_approval_history.result == 1

        # Assertion : Skipped (approved)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 1). \
            first()
        assert transfer_approval_history.exchange_address is None
        assert transfer_approval_history.result == 2

        # Assertion : Skipped (cancelled)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 2). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token issuer does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_issuer_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (manually approval)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "manual_token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        _expected = {
            "application_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address="token_address",
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )

    # <Normal_1_3>
    # tx_receipt status is 1 (Success)
    # Apply from IbetSecurityTokenEscrow
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_1_3(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : Token (issuer does not exist)
        dummy_issuer_token = Token()
        dummy_issuer_token.type = TokenType.IBET_SHARE
        dummy_issuer_token.token_address = "dummy_issuer_token_address"
        dummy_issuer_token.issuer_address = "ISSUER_DUMMY_ADDRESS"
        dummy_issuer_token.abi = "abi"
        dummy_issuer_token.tx_hash = "tx_hash"
        db.add(dummy_issuer_token)

        # Prepare data : Token (manually approval)
        manual_token = Token()
        manual_token.type = TokenType.IBET_STRAIGHT_BOND
        manual_token.token_address = "manual_token_address"
        manual_token.issuer_address = _account
        manual_token.abi = "abi"
        manual_token.tx_hash = "tx_hash"
        db.add(manual_token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval_0 = IDXTransferApproval()
        idx_transfer_approval_0.token_address = "token_address"
        idx_transfer_approval_0.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_0.application_id = 0
        idx_transfer_approval_0.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_0)

        # Prepare data : IDXTransferApproval, TransferApprovalHistory(approved)
        idx_transfer_approval_1 = IDXTransferApproval()
        idx_transfer_approval_1.token_address = "token_address"
        idx_transfer_approval_1.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_1.application_id = 1
        idx_transfer_approval_1.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_1)

        transfer_approval_history = TransferApprovalHistory()
        transfer_approval_history.token_address = "token_address"
        transfer_approval_history.exchange_address = "0x1234567890123456789012345678901234567890"
        transfer_approval_history.application_id = 1
        transfer_approval_history.result = 2
        db.add(transfer_approval_history)

        # Prepare data : IDXTransferApproval(cancelled)
        idx_transfer_approval_2 = IDXTransferApproval()
        idx_transfer_approval_2.token_address = "token_address"
        idx_transfer_approval_2.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_2.application_id = 2
        idx_transfer_approval_2.application_blocktimestamp = datetime.datetime.utcnow()
        idx_transfer_approval_2.cancelled = True
        db.add(idx_transfer_approval_2)

        # Prepare data : IDXTransferApproval(Token does not exists)
        idx_transfer_approval_4 = IDXTransferApproval()
        idx_transfer_approval_4.token_address = "dummy_token_address"
        idx_transfer_approval_4.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_4.application_id = 0
        idx_transfer_approval_4.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_4)
        db.commit()

        # Prepare data : IDXTransferApproval(manually approval)
        idx_transfer_approval_5 = IDXTransferApproval()
        idx_transfer_approval_5.token_address = "manual_token_address"
        idx_transfer_approval_5.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_5.application_id = 0
        idx_transfer_approval_5.application_blocktimestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(idx_transfer_approval_5)
        db.commit()

        # Prepare data : AdditionalTokenInfo(manually approval)
        additional_token_info_1 = AdditionalTokenInfo()
        additional_token_info_1.token_address = "manual_token_address"
        additional_token_info_1.is_manual_transfer_approval = None
        additional_token_info_1.block_number = 1
        additional_token_info_1.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 0)
        db.add(additional_token_info_1)
        additional_token_info_2 = AdditionalTokenInfo()
        additional_token_info_2.token_address = "manual_token_address"
        additional_token_info_2.is_manual_transfer_approval = False
        additional_token_info_2.block_number = 2
        additional_token_info_2.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 1)
        db.add(additional_token_info_2)
        additional_token_info_3 = AdditionalTokenInfo()
        additional_token_info_3.token_address = "manual_token_address"
        additional_token_info_3.is_manual_transfer_approval = True
        additional_token_info_3.block_number = 3
        additional_token_info_3.block_timestamp = datetime.datetime(2020, 1, 1, 12, 59, 59)
        db.add(additional_token_info_3)
        additional_token_info_4 = AdditionalTokenInfo()
        additional_token_info_4.token_address = "manual_token_address"
        additional_token_info_4.is_manual_transfer_approval = False
        additional_token_info_4.block_number = 4
        additional_token_info_4.block_timestamp = datetime.datetime(2020, 1, 1, 13, 0, 0)
        db.add(additional_token_info_4)
        db.commit()

        # mock
        IbetSecurityTokenEscrow_approve_transfer = patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            return_value=("test_tx_hash", {"status": 1})
        )

        with IbetSecurityTokenEscrow_approve_transfer as mock_transfer:
            # Execute batch
            processor.process()

        # Assertion : Success
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history.result == 1

        # Assertion : Skipped (approved)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 1). \
            first()
        assert transfer_approval_history.result == 2

        # Assertion : Skipped (cancelled)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 2). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (Token issuer does not exists)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "dummy_issuer_token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        # Assertion: Skipped (manually approval)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "manual_token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

        _expected = {
            "escrow_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            data=IbetSecurityTokenEscrowApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )

    # <Normal_2_1>
    # tx_receipt status is 0 (Fail)
    # Token
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_1(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval_0 = IDXTransferApproval()
        idx_transfer_approval_0.token_address = "token_address"
        idx_transfer_approval_0.application_id = 0
        idx_transfer_approval_0.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_0)

        # Prepare data : IDXTransferApproval(cancelled)
        idx_transfer_approval_1 = IDXTransferApproval()
        idx_transfer_approval_1.token_address = "token_address"
        idx_transfer_approval_1.application_id = 1
        idx_transfer_approval_1.application_blocktimestamp = datetime.datetime.utcnow()
        idx_transfer_approval_1.cancelled = True
        db.add(idx_transfer_approval_1)
        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            return_value=("test_tx_hash", {"status": 0})
        )

        IbetSecurityTokenContract_cancel_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.cancel_transfer",
        )

        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            with IbetSecurityTokenContract_cancel_transfer as mock_cancel:
                # Execute batch
                processor.process()

        # Assertion : Fail approve, and Cancelled
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history.exchange_address is None
        assert transfer_approval_history.result == 2

        # Assertion: Skipped (already cancelled)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 1). \
            first()
        assert transfer_approval_history is None

        _expected = {
            "application_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address="token_address",
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )
        mock_cancel.assert_called_once_with(
            contract_address="token_address",
            data=IbetSecurityTokenCancelTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )

    # <Normal_2_2>
    # tx_receipt status is 0 (Fail)
    # Exchange
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_normal_2_2(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval_0 = IDXTransferApproval()
        idx_transfer_approval_0.token_address = "token_address"
        idx_transfer_approval_0.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_0.application_id = 0
        idx_transfer_approval_0.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval_0)

        # Prepare data : IDXTransferApproval(cancelled)
        idx_transfer_approval_1 = IDXTransferApproval()
        idx_transfer_approval_1.token_address = "token_address"
        idx_transfer_approval_1.exchange_address = "0x1234567890123456789012345678901234567890"
        idx_transfer_approval_1.application_id = 1
        idx_transfer_approval_1.application_blocktimestamp = datetime.datetime.utcnow()
        idx_transfer_approval_1.cancelled = True
        db.add(idx_transfer_approval_1)
        db.commit()

        # mock
        IbetSecurityTokenEscrow_approve_transfer = patch(
            target="app.model.blockchain.exchange.IbetSecurityTokenEscrow.approve_transfer",
            return_value=("test_tx_hash", {"status": 0})
        )

        with IbetSecurityTokenEscrow_approve_transfer as mock_transfer:
            # Execute batch
            processor.process()

        # Assertion : Fail approve
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history.result == 2

        # Assertion: Skipped (already cancelled)
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.exchange_address == "0x1234567890123456789012345678901234567890"). \
            filter(TransferApprovalHistory.application_id == 1). \
            first()
        assert transfer_approval_history is None

        _expected = {
            "escrow_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            data=IbetSecurityTokenEscrowApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )

    # <Normal_3>
    # IDXTransferApproval is None
    def test_normal_3(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # No data : IDXTransferApproval
        # Execute batch
        processor.process()

        # Assertion
        transfer_approval_history = db.query(TransferApprovalHistory).all()
        assert len(transfer_approval_history) == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # exception during getting the private key
    def test_error_1(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : IDXTransferApproval
        # cancelled is None, not approved
        idx_transfer_approval = IDXTransferApproval()
        idx_transfer_approval.token_address = "token_address"
        idx_transfer_approval.application_id = 0
        idx_transfer_approval.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval)

        # mock
        IbetSecurityTokenContract_approve_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
        )
        E2EEUtils_decrypt = patch(
            target="app.utils.e2ee_utils.E2EEUtils.decrypt",
            side_effect=ValueError("test")
        )

        with E2EEUtils_decrypt as mock_decrypt:
            with IbetSecurityTokenContract_approve_transfer as mock_transfer:
                # Execute batch
                processor.process()

        # Assertion: Skipped
        mock_decrypt.assert_called_once()
        mock_transfer.assert_not_called()
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None

    # <Error_2>
    # exception during send transaction
    @pytest.mark.freeze_time('2021-04-27 12:34:56')
    def test_error_2(self, processor, db):
        _account = config_eth_account("user1")["address"]
        _keyfile = config_eth_account("user1")["keyfile_json"]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _keyfile
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_SHARE
        token.token_address = "token_address"
        token.issuer_address = _account
        token.abi = "abi"
        token.tx_hash = "tx_hash"
        db.add(token)

        # Prepare data : IDXTransferApproval
        idx_transfer_approval = IDXTransferApproval()
        idx_transfer_approval.token_address = "token_address"
        idx_transfer_approval.application_id = 0
        idx_transfer_approval.application_blocktimestamp = datetime.datetime.utcnow()
        db.add(idx_transfer_approval)
        db.commit()

        # mock
        IbetSecurityTokenContract_approve_transfer = patch(
            target="app.model.blockchain.token.IbetSecurityTokenInterface.approve_transfer",
            side_effect=SendTransactionError()
        )

        with IbetSecurityTokenContract_approve_transfer as mock_transfer:
            # Execute batch
            processor.process()

        # Assertion: Skipped
        _expected = {
            "application_id": 0,
            "data": str(datetime.datetime.utcnow().timestamp())
        }

        mock_transfer.assert_called_once_with(
            contract_address="token_address",
            data=IbetSecurityTokenApproveTransfer(**_expected),
            tx_from=_account,
            private_key=ANY
        )
        transfer_approval_history = db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == "token_address"). \
            filter(TransferApprovalHistory.application_id == 0). \
            first()
        assert transfer_approval_history is None
