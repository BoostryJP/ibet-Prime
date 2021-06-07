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
from unittest.mock import patch

from app.model.db import (
    Account,
    BulkTransfer,
    BulkTransferUpload,
    TokenType,
    Notification,
    NotificationType
)
from app.utils.e2ee_utils import E2EEUtils
from app.exceptions import SendTransactionError
from batch.processor_bulk_transfer import (
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
    account_list = [
        {
            "address": config_eth_account("user1")["address"],
            "keyfile": config_eth_account("user1")["keyfile_json"]
        }, {
            "address": config_eth_account("user2")["address"],
            "keyfile": config_eth_account("user2")["keyfile_json"]
        }, {
            "address": config_eth_account("user3")["address"],
            "keyfile": config_eth_account("user3")["keyfile_json"]
        }
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
        "0f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
        "1c961f7d-e1ad-40e5-988b-cca3d6009643",
        "1e778f46-864e-4ec0-b566-21bd31cf63ff",
        "1f33d48f-9e6e-4a36-a55e-5bbcbda69c80"
    ]

    bulk_transfer_token = [
        "0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca",
        "0x55e20Fa9F4Fa854Ef06081734872b734c105916b",
        "0x1d2E98AD049e978B08113fD282BD42948F265DDa",
        "0x2413a63D91eb10e1472a18aD4b9628fBE4aac8B8",
        "0x6f9486251F4034C251ecb8Fa0f087CDDb3cDe6d7",
        "0xd40a1F59c29776B164857bA48AF415CeA072aC98",
    ]

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # IbetStraightBond
    def test_normal_1(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        # Only record 0 should be processed
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = _account["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer.token_address = self.bulk_transfer_token[i]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.transfer",
            return_value=None
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            processor.process()

            # Assertion
            _bulk_transfer_upload = db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
                first()
            assert _bulk_transfer_upload.status == 1

            _bulk_transfer_list = db.query(BulkTransfer). \
                filter(BulkTransfer.upload_id == self.upload_id_list[0]). \
                all()
            for _bulk_transfer in _bulk_transfer_list:
                assert _bulk_transfer.status == 1

    # <Normal_2>
    # IbetShare
    def test_normal_2(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        # Only record 0 should be processed
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = _account["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_SHARE
            bulk_transfer.token_address = self.bulk_transfer_token[i]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetShareContract_transfer = patch(
            target="app.model.blockchain.token.IbetShareContract.transfer",
            return_value=None
        )

        with IbetShareContract_transfer:
            # Execute batch
            processor.process()

            # Assertion
            _bulk_transfer_upload = db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
                first()
            assert _bulk_transfer_upload.status == 1

            _bulk_transfer_list = db.query(BulkTransfer). \
                filter(BulkTransfer.upload_id == self.upload_id_list[0]). \
                all()
            for _bulk_transfer in _bulk_transfer_list:
                assert _bulk_transfer.status == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Account does not exist
    def test_error_1(self, processor, db):
        _account = self.account_list[0]

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
        bulk_transfer_upload.status = 0  # pending
        db.add(bulk_transfer_upload)

        db.commit()

        # Execute batch
        processor.process()

        # Assertion
        _bulk_transfer_upload = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
            first()
        assert _bulk_transfer_upload.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _account["address"]
        assert _notification.priority == 1
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "upload_id": self.upload_id_list[0],
            "error_transfer_id": []
        }

    # <Error_2>
    # fail to get the private key
    def test_error_2(self, processor, db):
        _account = self.account_list[0]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password_ng")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
        bulk_transfer_upload.status = 0  # pending
        db.add(bulk_transfer_upload)

        db.commit()

        # Execute batch
        processor.process()

        # Assertion
        _bulk_transfer_upload = db.query(BulkTransferUpload). \
            filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
            first()
        assert _bulk_transfer_upload.status == 2
        _notification = db.query(Notification).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _account["address"]
        assert _notification.priority == 1
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "upload_id": self.upload_id_list[0],
            "error_transfer_id": []
        }

    # <Error_3>
    # Send Transaction Error: IbetStraightBond
    def test_error_3(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        bulk_transfer = BulkTransfer()
        bulk_transfer.issuer_address = _account["address"]
        bulk_transfer.upload_id = self.upload_id_list[0]
        bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
        bulk_transfer.token_address = self.bulk_transfer_token[0]
        bulk_transfer.from_address = _from_address["address"]
        bulk_transfer.to_address = _to_address["address"]
        bulk_transfer.amount = 1
        bulk_transfer.status = 0  # pending:0
        db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.transfer",
            side_effect=SendTransactionError()
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            processor.process()

            # Assertion
            _bulk_transfer_upload = db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
                first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.query(BulkTransfer). \
                filter(BulkTransfer.upload_id == self.upload_id_list[0]). \
                filter(BulkTransfer.token_address == self.bulk_transfer_token[0]). \
                first()
            assert _bulk_transfer.status == 2

            _notification = db.query(Notification).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "error_transfer_id": [1]
            }

    # <Error_4>
    # Send Transaction Error: IbetShare
    def test_error_4(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_SHARE
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        bulk_transfer = BulkTransfer()
        bulk_transfer.issuer_address = _account["address"]
        bulk_transfer.upload_id = self.upload_id_list[0]
        bulk_transfer.token_type = TokenType.IBET_SHARE
        bulk_transfer.token_address = self.bulk_transfer_token[0]
        bulk_transfer.from_address = _from_address["address"]
        bulk_transfer.to_address = _to_address["address"]
        bulk_transfer.amount = 1
        bulk_transfer.status = 0  # pending:0
        db.add(bulk_transfer)

        db.commit()

        # mock
        IbetShareContract_transfer = patch(
            target="app.model.blockchain.token.IbetShareContract.transfer",
            side_effect=SendTransactionError()
        )

        with IbetShareContract_transfer:
            # Execute batch
            processor.process()

            # Assertion
            _bulk_transfer_upload = db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
                first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.query(BulkTransfer). \
                filter(BulkTransfer.upload_id == self.upload_id_list[0]). \
                filter(BulkTransfer.token_address == self.bulk_transfer_token[0]). \
                first()
            assert _bulk_transfer.status == 2

            _notification = db.query(Notification).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "error_transfer_id": [1]
            }

    # <Error_5>
    # Process down after error occurred, Re-run process
    def test_error_5(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        # Only record 0 should be processed
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = _account["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
            bulk_transfer.token_address = self.bulk_transfer_token[i]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.transfer",
            return_value=None
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            processor.process()

            # Assertion
            _bulk_transfer_upload = db.query(BulkTransferUpload). \
                filter(BulkTransferUpload.upload_id == self.upload_id_list[0]). \
                first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.query(BulkTransfer). \
                filter(BulkTransfer.upload_id == self.upload_id_list[0]). \
                filter(BulkTransfer.token_address == self.bulk_transfer_token[0]). \
                first()
            assert _bulk_transfer.status == 1

            _notification = db.query(Notification).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "error_transfer_id": [3]
            }

