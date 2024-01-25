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
from typing import List, Sequence
from unittest.mock import ANY, patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain.tx_params.ibet_share import (
    AdditionalIssueParams as IbetShareAdditionalIssueParams,
    RedeemParams as IbetShareRedeemParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    AdditionalIssueParams as IbetStraightBondAdditionalIssueParams,
    RedeemParams as IbetStraightBondRedeemParams,
)
from app.model.db import (
    Account,
    BatchIssueRedeem,
    BatchIssueRedeemProcessingCategory,
    BatchIssueRedeemUpload,
    Notification,
    NotificationType,
    TokenType,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_batch_issue_redeem import LOG, Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
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
    @pytest.mark.asyncio
    async def test_normal_1(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8"),
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
            return_value="mock_tx_hash",
        ) as IbetStraightBondContract_additional_issue:
            await processor.process()

            # Assertion: contract
            IbetStraightBondContract_additional_issue.assert_called_with(
                data=IbetStraightBondAdditionalIssueParams(
                    account_address=target_address, amount=target_amount
                ),
                tx_from=issuer_address,
                private_key=issuer_pk,
            )

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 1

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.DEBUG, "Transaction sent successfully: mock_tx_hash")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 0  # Successful
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
            }

    # Normal_2
    # token type: IBET_STRAIGHT_BOND
    # processing category: REDEEM
    @pytest.mark.asyncio
    async def test_normal_2(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8"),
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
            return_value="mock_tx_hash",
        ) as IbetStraightBondContract_redeem:
            await processor.process()

        # Assertion: contract
        IbetStraightBondContract_redeem.assert_called_with(
            data=IbetStraightBondRedeemParams(
                account_address=target_address, amount=target_amount
            ),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 1

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.DEBUG, "Transaction sent successfully: mock_tx_hash")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 0  # Successful
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.REDEEM.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
            }

    # Normal_3
    # token type: IBET_SHARE
    # processing category: ISSUE
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8"),
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
            return_value="mock_tx_hash",
        ) as IbetShareContract_additional_issue:
            await processor.process()

        # Assertion: contract
        IbetShareContract_additional_issue.assert_called_with(
            data=IbetShareAdditionalIssueParams(
                account_address=target_address, amount=target_amount
            ),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 1

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.DEBUG, "Transaction sent successfully: mock_tx_hash")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 0  # Successful
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_SHARE,
            }

    # Normal_4
    # token type: IBET_SHARE
    # processing category: REDEEM
    @pytest.mark.asyncio
    async def test_normal_4(self, processor, db, caplog):
        # Test settings
        issuer_account = config_eth_account("user1")
        issuer_address = issuer_account["address"]
        issuer_keyfile = issuer_account["keyfile_json"]
        issuer_eoa_password = E2EEUtils.encrypt("password")
        issuer_pk = decode_keyfile_json(
            raw_keyfile_json=issuer_keyfile,
            password=E2EEUtils.decrypt(issuer_eoa_password).encode("utf-8"),
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
            return_value="mock_tx_hash",
        ) as IbetShareContract_redeem:
            await processor.process()

        # Assertion: contract
        IbetShareContract_redeem.assert_called_with(
            data=IbetShareRedeemParams(
                account_address=target_address, amount=target_amount
            ),
            tx_from=issuer_address,
            private_key=issuer_pk,
        )

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 1

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.DEBUG, "Transaction sent successfully: mock_tx_hash")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 0  # Successful
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.REDEEM.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_SHARE,
            }

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # Issuer account does not exist
    @pytest.mark.asyncio
    async def test_error_1(self, processor, db, caplog):
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
            return_value="mock_tx_hash",
        ) as IbetStraightBondContract_additional_issue:
            await processor.process()

        # Assertion: contract
        IbetStraightBondContract_additional_issue.assert_not_called()

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 0

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.ERROR, "Issuer account does not exist")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 1  # Failed
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
            }

    # Error_2
    # Failed to decode keyfile
    @pytest.mark.asyncio
    async def test_error_2(self, processor, db, caplog):
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
            return_value="mock_tx_hash",
        ) as IbetStraightBondContract_additional_issue:
            await processor.process()

        # Assertion: contract
        IbetStraightBondContract_additional_issue.assert_not_called()

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 1
        assert _upload_data_after[0].status == 0

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.ERROR, "Failed to decode keyfile")
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 2  # Failed
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                "upload_id": upload_id,
                "error_data_id": [],
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
            }

    # Error_3
    # Failed to send transaction
    @pytest.mark.asyncio
    async def test_error_3(self, processor, db, caplog):
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

        _upload_data_1 = BatchIssueRedeem()
        _upload_data_1.upload_id = upload_id
        _upload_data_1.account_address = target_address
        _upload_data_1.amount = target_amount
        _upload_data_1.status = 0
        db.add(_upload_data_1)

        _upload_data_2 = BatchIssueRedeem()
        _upload_data_2.upload_id = upload_id
        _upload_data_2.account_address = target_address
        _upload_data_2.amount = target_amount
        _upload_data_2.status = 0
        db.add(_upload_data_2)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
            side_effect=SendTransactionError(),
        ) as IbetStraightBondContract_additional_issue:
            await processor.process()

        # Assertion: DB
        _upload_after: BatchIssueRedeemUpload = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_id)
            .limit(1)
        ).first()
        assert _upload_after.processed == True

        _upload_data_after: List[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_id)
        ).all()
        assert len(_upload_data_after) == 2
        assert _upload_data_after[0].status == 2
        assert _upload_data_after[1].status == 2

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (LOG.name, logging.WARNING, "Failed to send transaction: -")
            )
            == 2
        )

        _notification_list = db.scalars(select(Notification)).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == issuer_address
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
            assert _notification.code == 3  # Failed
            assert _notification.metainfo == {
                "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
                "upload_id": upload_id,
                "error_data_id": ANY,
                "token_address": token_address,
                "token_type": TokenType.IBET_STRAIGHT_BOND,
            }
            assert len(_notification.metainfo["error_data_id"]) == 2

    # <Error_4>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_4(
        self, processor: Processor, db: Session, caplog: pytest.LogCaptureFixture
    ):
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

        upload_1_id = str(uuid.uuid4())

        _upload_1 = BatchIssueRedeemUpload()
        _upload_1.upload_id = upload_1_id
        _upload_1.issuer_address = issuer_address
        _upload_1.token_type = TokenType.IBET_STRAIGHT_BOND.value
        _upload_1.token_address = token_address
        _upload_1.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload_1.processed = 0
        db.add(_upload_1)

        _upload_data_1 = BatchIssueRedeem()
        _upload_data_1.upload_id = upload_1_id
        _upload_data_1.account_address = target_address
        _upload_data_1.amount = target_amount
        _upload_data_1.status = 0
        db.add(_upload_data_1)

        upload_2_id = str(uuid.uuid4())

        _upload_2 = BatchIssueRedeemUpload()
        _upload_2.upload_id = upload_2_id
        _upload_2.issuer_address = issuer_address
        _upload_2.token_type = TokenType.IBET_SHARE.value
        _upload_2.token_address = token_address
        _upload_2.category = BatchIssueRedeemProcessingCategory.ISSUE.value
        _upload_2.processed = 0
        db.add(_upload_2)

        _upload_data_2 = BatchIssueRedeem()
        _upload_data_2.upload_id = upload_2_id
        _upload_data_2.account_address = target_address
        _upload_data_2.amount = target_amount
        _upload_data_2.status = 0
        db.add(_upload_data_2)

        db.commit()

        # mock
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.additional_issue",
            side_effect=ContractRevertError("999999"),
        ), patch(
            target="app.model.blockchain.token.IbetShareContract.additional_issue",
            side_effect=ContractRevertError("999999"),
        ):
            await processor.process()

        # Assertion: DB
        _upload_1_after: BatchIssueRedeemUpload | None = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_1_id)
            .limit(1)
        ).first()
        assert _upload_1_after.processed == True

        _upload_1_data_after: Sequence[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_1_id)
        ).all()
        assert len(_upload_1_data_after) == 1
        assert _upload_1_data_after[0].status == 2

        _upload_2_after: BatchIssueRedeemUpload | None = db.scalars(
            select(BatchIssueRedeemUpload)
            .where(BatchIssueRedeemUpload.upload_id == upload_2_id)
            .limit(1)
        ).first()
        assert _upload_2_after.processed == True

        _upload_2_data_after: Sequence[BatchIssueRedeem] = db.scalars(
            select(BatchIssueRedeem).where(BatchIssueRedeem.upload_id == upload_2_id)
        ).all()
        assert len(_upload_2_data_after) == 1
        assert _upload_2_data_after[0].status == 2

        # Assertion: Log
        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARNING,
                    f"Transaction reverted: upload_id=<{_upload_1_after.upload_id}> error_code:<999999> error_msg:<>",
                )
            )
            == 1
        )
        assert (
            caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARNING,
                    f"Transaction reverted: upload_id=<{_upload_2_after.upload_id}> error_code:<999999> error_msg:<>",
                )
            )
            == 1
        )

        _notification_list = db.scalars(select(Notification)).all()
        assert _notification_list[0].notice_id is not None
        assert _notification_list[0].issuer_address == issuer_address
        assert _notification_list[0].priority == 1
        assert (
            _notification_list[0].type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
        )
        assert _notification_list[0].code == 3  # Failed
        assert _notification_list[0].metainfo == {
            "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
            "upload_id": upload_1_id,
            "error_data_id": ANY,
            "token_address": token_address,
            "token_type": TokenType.IBET_STRAIGHT_BOND,
        }
        assert len(_notification_list[0].metainfo["error_data_id"]) == 1

        assert _notification_list[1].notice_id is not None
        assert _notification_list[1].issuer_address == issuer_address
        assert _notification_list[1].priority == 1
        assert (
            _notification_list[1].type == NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
        )
        assert _notification_list[1].code == 3  # Failed
        assert _notification_list[1].metainfo == {
            "category": BatchIssueRedeemProcessingCategory.ISSUE.value,
            "upload_id": upload_2_id,
            "error_data_id": ANY,
            "token_address": token_address,
            "token_type": TokenType.IBET_SHARE,
        }
        assert len(_notification_list[1].metainfo["error_data_id"]) == 1
