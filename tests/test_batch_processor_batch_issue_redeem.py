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
import logging
import uuid
from typing import List
from unittest.mock import patch

import pytest

from eth_keyfile import decode_keyfile_json

from app.exceptions import SendTransactionError
from app.model.db import (
    Account,
    BatchIssueRedeemUpload,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeem,
    TokenType
)
from app.model.schema import (
    IbetStraightBondAdditionalIssue,
    IbetStraightBondRedeem,
    IbetShareAdditionalIssue,
    IbetShareRedeem
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_batch_issue_redeem import Processor, LOG
from tests.account_config import config_eth_account


@pytest.fixture(scope='function')
def processor(db, caplog: pytest.LogCaptureFixture):
    log = logging.getLogger("background")
    default_log_level = LOG.level
    log.setLevel(logging.DEBUG)
    log.propagate = True
    yield Processor()
    log.propagate = False
    log.setLevel(default_log_level)


class TestProcessor:

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # token type: IBET_STRAIGHT_BOND
    # processing category: ISSUE
    def test_normal_1(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8")
        )

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
                return_value="mock_tx_hash") as IbetStraightBondContract_additional_issue:
            processor.process()

            # Assertion: contract
            IbetStraightBondContract_additional_issue.assert_called_with(
                contract_address=token_address,
                data=IbetStraightBondAdditionalIssue(
                    account_address=target_address,
                    amount=target_amount
                ),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 1

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.DEBUG,
                "Transaction sent successfully: mock_tx_hash"
            )) == 1

    # Normal_2
    # token type: IBET_STRAIGHT_BOND
    # processing category: REDEEM
    def test_normal_2(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8")
        )

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetStraightBondContract.redeem",
                return_value="mock_tx_hash") as IbetStraightBondContract_redeem:
            processor.process()

            # Assertion: contract
            IbetStraightBondContract_redeem.assert_called_with(
                contract_address=token_address,
                data=IbetStraightBondRedeem(
                    account_address=target_address,
                    amount=target_amount
                ),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 1

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.DEBUG,
                "Transaction sent successfully: mock_tx_hash"
            )) == 1

    # Normal_3
    # token type: IBET_SHARE
    # processing category: ISSUE
    def test_normal_3(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8")
        )

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_SHARE.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetShareContract.additional_issue",
                return_value="mock_tx_hash") as IbetShareContract_additional_issue:
            processor.process()

            # Assertion: contract
            IbetShareContract_additional_issue.assert_called_with(
                contract_address=token_address,
                data=IbetShareAdditionalIssue(
                    account_address=target_address,
                    amount=target_amount
                ),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 1

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.DEBUG,
                "Transaction sent successfully: mock_tx_hash"
            )) == 1

    # Normal_4
    # token type: IBET_SHARE
    # processing category: REDEEM
    def test_normal_4(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8")
        )

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_SHARE.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.REDEEM.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetShareContract.redeem",
                return_value="mock_tx_hash") as IbetShareContract_redeem:
            processor.process()

            # Assertion: contract
            IbetShareContract_redeem.assert_called_with(
                contract_address=token_address,
                data=IbetShareRedeem(
                    account_address=target_address,
                    amount=target_amount
                ),
                tx_from=issuer_address,
                private_key=issuer_pk
            )

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 1

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.DEBUG,
                "Transaction sent successfully: mock_tx_hash"
            )) == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # Issuer account does not exist
    def test_error_1(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
                return_value="mock_tx_hash") as IbetStraightBondContract_additional_issue:
            processor.process()

            # Assertion: contract
            IbetStraightBondContract_additional_issue.assert_not_called()

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 0

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.ERROR,
                "Issuer account does not exist"
            )) == 1

    # Error_2
    # Failed to decode keyfile
    def test_error_2(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("wrong_password")  # wrong password

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
                return_value="mock_tx_hash") as IbetStraightBondContract_additional_issue:
            processor.process()

            # Assertion: contract
            IbetStraightBondContract_additional_issue.assert_not_called()

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 0

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.ERROR,
                "Failed to decode keyfile"
            )) == 1

    # Error_3
    # Failed to send transaction
    def test_error_3(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")

        token_address = "test_token_address"

        target_account = config_eth_account("user2")
        target_address = target_account["address"]
        target_amount = 10

        # Prepare data
        _account = Account()
        _account.issuer_address = issuer_address
        _account.keyfile = issuer_keyfile
        _account.eoa_password = issuer_eoa_password
        _account.rsa_status = 3
        db.add(_account)

        upload_id = str(uuid.uuid4())

        _upload = BatchIssueRedeemUpload()
        _upload.upload_id = upload_id
        _upload.issuer_address = issuer_address
        _upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload.token_address = token_address
        _upload.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload.processed = 0
        db.add(_upload)

        _upload_data = BatchIssueRedeem()
        _upload_data.upload_id = upload_id
        _upload_data.account_address = target_address
        _upload_data.amount = target_amount
        _upload_data.status = 0
        db.add(_upload_data)

        db.commit()

        # Execute batch
        with patch(
                target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
                side_effect=SendTransactionError()) as IbetStraightBondContract_additional_issue:
            processor.process()

            # Assertion: DB
            _upload_after: BatchIssueRedeemUpload = db.query(BatchIssueRedeemUpload). \
                filter(BatchIssueRedeemUpload.upload_id == upload_id). \
                first()
            assert _upload_after.processed == True

            _upload_data_after: List[BatchIssueRedeem] = db.query(BatchIssueRedeem). \
                filter(BatchIssueRedeem.upload_id == upload_id). \
                all()
            assert len(_upload_data_after) == 1
            assert _upload_data_after[0].status == 2

            # Assertion: Log
            assert caplog.record_tuples.count((
                LOG.name,
                logging.WARNING,
                "Failed to send transaction: -"
            )) == 1
