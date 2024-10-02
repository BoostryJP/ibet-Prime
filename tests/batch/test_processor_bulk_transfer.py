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

import asyncio
from unittest.mock import ANY, patch

import pytest
from sqlalchemy import and_, select

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain.tx_params.ibet_security_token import ForcedTransferParams
from app.model.db import (
    Account,
    BulkTransfer,
    BulkTransferUpload,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.utils.e2ee_utils import E2EEUtils
from batch.processor_bulk_transfer import Processor
from tests.account_config import config_eth_account


@pytest.fixture(scope="function")
def processor(db):
    return Processor(worker_num=0, is_shutdown=asyncio.Event())


class TestProcessor:
    account_list = [
        {
            "address": config_eth_account("user1")["address"],
            "keyfile": config_eth_account("user1")["keyfile_json"],
        },
        {
            "address": config_eth_account("user2")["address"],
            "keyfile": config_eth_account("user2")["keyfile_json"],
        },
        {
            "address": config_eth_account("user3")["address"],
            "keyfile": config_eth_account("user3")["keyfile_json"],
        },
    ]

    upload_id_list = [
        "0c961f7d-e1ad-40e5-988b-cca3d6009643",
        "0e778f46-864e-4ec0-b566-21bd31cf63ff",
        "0f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
        "1c961f7d-e1ad-40e5-988b-cca3d6009643",
        "1e778f46-864e-4ec0-b566-21bd31cf63ff",
        "1f33d48f-9e6e-4a36-a55e-5bbcbda69c80",
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

    # <Normal_1_1>
    # ~v24.6: Transfer individually
    # IbetStraightBond
    @pytest.mark.asyncio
    async def test_normal_1_1(self, processor, db):
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
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer_upload.token_address = self.bulk_transfer_token[i]
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            return_value=None,
        ) as IbetStraightBondContract_transfer:
            await processor.process()

        # Assertion
        IbetStraightBondContract_transfer.assert_called_with(
            data=ForcedTransferParams(
                from_address=_from_address["address"],
                to_address=_to_address["address"],
                amount=1,
            ),
            tx_from=_account["address"],
            private_key=ANY,
        )

        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 1
        assert _bulk_transfer_upload[1].status == 1
        assert _bulk_transfer_upload[2].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 1

    # <Normal_1_2>
    # ~v24.6: Transfer individually
    # IbetShare
    @pytest.mark.asyncio
    async def test_normal_1_2(self, processor, db):
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
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.token_address = self.bulk_transfer_token[i]
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_SHARE.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetShareContract.forced_transfer",
            return_value=None,
        ) as IbetShareContract_transfer:
            await processor.process()

        # Assertion
        IbetShareContract_transfer.assert_called_with(
            data=ForcedTransferParams(
                from_address=_from_address["address"],
                to_address=_to_address["address"],
                amount=1,
            ),
            tx_from=_account["address"],
            private_key=ANY,
        )

        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 1
        assert _bulk_transfer_upload[1].status == 1
        assert _bulk_transfer_upload[2].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 1

    # <Normal_2_1>
    # v24.9~: Transfer in batch
    # IbetStraightBond
    @pytest.mark.asyncio
    async def test_normal_2_1(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : Token
        for i in range(0, 3):
            token = Token()
            token.type = TokenType.IBET_STRAIGHT_BOND.value
            token.token_address = self.bulk_transfer_token[i]
            token.issuer_address = _account["address"]
            token.abi = {}
            token.tx_hash = ""
            token.version = TokenVersion.V_24_09
            db.add(token)

        # Prepare data : BulkTransferUpload
        # Only record 0 should be processed
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = _account["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer_upload.token_address = self.bulk_transfer_token[i]
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.bulk_forced_transfer",
            return_value=None,
        ) as IbetStraightBondContract_bulk_transfer:
            await processor.process()

        # Assertion
        IbetStraightBondContract_bulk_transfer.assert_called_with(
            data=[
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
            ],
            tx_from=_account["address"],
            private_key=ANY,
        )

        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 1
        assert _bulk_transfer_upload[1].status == 1
        assert _bulk_transfer_upload[2].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 1

    # <Normal_2_2>
    # v24.9~: Transfer in batch
    # IbetShare
    @pytest.mark.asyncio
    async def test_normal_2_2(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : Token
        for i in range(0, 3):
            token = Token()
            token.type = TokenType.IBET_SHARE.value
            token.token_address = self.bulk_transfer_token[i]
            token.issuer_address = _account["address"]
            token.abi = {}
            token.tx_hash = ""
            token.version = TokenVersion.V_24_09
            db.add(token)

        # Prepare data : BulkTransferUpload
        # Only record 0 should be processed
        for i in range(0, 3):
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = _account["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            bulk_transfer_upload.token_type = TokenType.IBET_SHARE.value
            bulk_transfer_upload.token_address = self.bulk_transfer_token[i]
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_SHARE.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetShareContract.bulk_forced_transfer",
            return_value=None,
        ) as IbetShareContract_bulk_transfer:
            await processor.process()

        # Assertion
        IbetShareContract_bulk_transfer.assert_called_with(
            data=[
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
                ForcedTransferParams(
                    from_address=_from_address["address"],
                    to_address=_to_address["address"],
                    amount=1,
                ),
            ],
            tx_from=_account["address"],
            private_key=ANY,
        )

        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 1
        assert _bulk_transfer_upload[1].status == 1
        assert _bulk_transfer_upload[2].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 1

    # <Normal_3>
    # Skip other thread processed issuer
    @patch("batch.processor_bulk_transfer.BULK_TRANSFER_WORKER_LOT_SIZE", 2)
    @pytest.mark.asyncio
    async def test_normal_3(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]
        _other_issuer_address_1 = "0x1234567890123456789012345678901234567890"

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = (
            _other_issuer_address_1  # other thread processed issuer
        )
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = (
            _other_issuer_address_1  # other thread processed issuer
        )
        bulk_transfer_upload.upload_id = self.upload_id_list[1]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[1]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _other_issuer_address_1  # skip issuer
        bulk_transfer_upload.upload_id = self.upload_id_list[2]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[2]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[3]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[3]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[4]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[4]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[3]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[3]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[4]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[4]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            return_value=None,
        )
        processing_issuer = patch(
            "batch.processor_bulk_transfer.processing_issuer",
            {
                1: {
                    self.upload_id_list[0]: _other_issuer_address_1,
                    self.upload_id_list[1]: _other_issuer_address_1,
                }
            },
        )

        with IbetStraightBondContract_transfer, processing_issuer:
            # Execute batch
            await processor.process()

            # Assertion
            _bulk_transfer_upload_list = db.scalars(
                select(BulkTransferUpload).order_by(BulkTransferUpload.created)
            ).all()
            _bulk_transfer_upload = _bulk_transfer_upload_list[0]
            assert _bulk_transfer_upload.status == 0
            _bulk_transfer_upload = _bulk_transfer_upload_list[1]
            assert _bulk_transfer_upload.status == 0
            _bulk_transfer_upload = _bulk_transfer_upload_list[2]
            assert _bulk_transfer_upload.status == 0
            _bulk_transfer_upload = _bulk_transfer_upload_list[3]
            assert _bulk_transfer_upload.status == 1
            _bulk_transfer_upload = _bulk_transfer_upload_list[4]
            assert _bulk_transfer_upload.status == 1

            _bulk_transfer_list = db.scalars(
                select(BulkTransfer)
                .where(BulkTransfer.upload_id == self.upload_id_list[3])
                .order_by(BulkTransfer.id)
            ).all()
            _bulk_transfer = _bulk_transfer_list[0]
            assert _bulk_transfer.status == 1

            _bulk_transfer_list = db.scalars(
                select(BulkTransfer)
                .where(BulkTransfer.upload_id == self.upload_id_list[4])
                .order_by(BulkTransfer.id)
            ).all()
            _bulk_transfer = _bulk_transfer_list[0]
            assert _bulk_transfer.status == 1

    # <Normal_4>
    # Other thread processed issuer(all same issuer)
    @patch("batch.processor_bulk_transfer.BULK_TRANSFER_WORKER_LOT_SIZE", 2)
    @pytest.mark.asyncio
    async def test_normal_4(self, processor, db):
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
        bulk_transfer_upload.issuer_address = _account[
            "address"
        ]  # other thread processed issuer
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account[
            "address"
        ]  # other thread processed issuer
        bulk_transfer_upload.upload_id = self.upload_id_list[1]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[1]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account[
            "address"
        ]  # other thread same issuer
        bulk_transfer_upload.upload_id = self.upload_id_list[2]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[2]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account[
            "address"
        ]  # other thread same issuer
        bulk_transfer_upload.upload_id = self.upload_id_list[3]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[3]
        bulk_transfer_upload.status = 0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[2]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[2]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[3]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[3]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            return_value=None,
        )
        processing_issuer = patch(
            "batch.processor_bulk_transfer.processing_issuer",
            {
                1: {
                    self.upload_id_list[0]: _account["address"],
                    self.upload_id_list[1]: _account["address"],
                }
            },
        )

        with IbetStraightBondContract_transfer, processing_issuer:
            # Execute batch
            await processor.process()

            # Assertion
            _bulk_transfer_upload_list = db.scalars(
                select(BulkTransferUpload).order_by(BulkTransferUpload.created)
            ).all()
            _bulk_transfer_upload = _bulk_transfer_upload_list[0]
            assert _bulk_transfer_upload.status == 0
            _bulk_transfer_upload = _bulk_transfer_upload_list[1]
            assert _bulk_transfer_upload.status == 0
            _bulk_transfer_upload = _bulk_transfer_upload_list[2]
            assert _bulk_transfer_upload.status == 1
            _bulk_transfer_upload = _bulk_transfer_upload_list[3]
            assert _bulk_transfer_upload.status == 1

            _bulk_transfer_list = db.scalars(
                select(BulkTransfer)
                .where(BulkTransfer.upload_id == self.upload_id_list[2])
                .order_by(BulkTransfer.id)
            ).all()
            _bulk_transfer = _bulk_transfer_list[0]
            assert _bulk_transfer.status == 1

            _bulk_transfer_list = db.scalars(
                select(BulkTransfer)
                .where(BulkTransfer.upload_id == self.upload_id_list[3])
                .order_by(BulkTransfer.id)
            ).all()
            _bulk_transfer = _bulk_transfer_list[0]
            assert _bulk_transfer.status == 1

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # Account does not exist
    @pytest.mark.asyncio
    async def test_error_1(self, processor, db):
        _account = self.account_list[0]

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending
        db.add(bulk_transfer_upload)

        db.commit()

        # Execute batch
        await processor.process()

        # Assertion
        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload)
            .where(BulkTransferUpload.upload_id == self.upload_id_list[0])
            .limit(1)
        ).first()
        assert _bulk_transfer_upload.status == 2

        _notification = db.scalars(select(Notification).limit(1)).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _account["address"]
        assert _notification.priority == 1
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 0
        assert _notification.metainfo == {
            "upload_id": self.upload_id_list[0],
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_address": self.bulk_transfer_token[0],
            "error_transfer_id": [],
        }

    # <Error_2>
    # fail to get the private key
    @pytest.mark.asyncio
    async def test_error_2(self, processor, db):
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
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending
        db.add(bulk_transfer_upload)

        db.commit()

        # Execute batch
        await processor.process()

        # Assertion
        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload)
            .where(BulkTransferUpload.upload_id == self.upload_id_list[0])
            .limit(1)
        ).first()
        assert _bulk_transfer_upload.status == 2

        _notification = db.scalars(select(Notification).limit(1)).first()
        assert _notification.id == 1
        assert _notification.notice_id is not None
        assert _notification.issuer_address == _account["address"]
        assert _notification.priority == 1
        assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
        assert _notification.code == 1
        assert _notification.metainfo == {
            "upload_id": self.upload_id_list[0],
            "token_type": TokenType.IBET_STRAIGHT_BOND.value,
            "token_address": self.bulk_transfer_token[0],
            "error_transfer_id": [],
        }

    # <Error_3_1>
    # ~v24.6: Transfer individually
    # SendTransactionError
    @pytest.mark.asyncio
    async def test_error_3_1(self, processor, db):
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
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        bulk_transfer = BulkTransfer()
        bulk_transfer.issuer_address = _account["address"]
        bulk_transfer.upload_id = self.upload_id_list[0]
        bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer.token_address = self.bulk_transfer_token[0]
        bulk_transfer.from_address = _from_address["address"]
        bulk_transfer.to_address = _to_address["address"]
        bulk_transfer.amount = 1
        bulk_transfer.status = 0  # pending:0
        db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            side_effect=SendTransactionError(),
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            await processor.process()

            # Assertion
            _bulk_transfer_upload = db.scalars(
                select(BulkTransferUpload)
                .where(BulkTransferUpload.upload_id == self.upload_id_list[0])
                .limit(1)
            ).first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.scalars(
                select(BulkTransfer)
                .where(
                    and_(
                        BulkTransfer.upload_id == self.upload_id_list[0],
                        BulkTransfer.token_address == self.bulk_transfer_token[0],
                    )
                )
                .limit(1)
            ).first()
            assert _bulk_transfer.status == 2

            _notification = db.scalars(select(Notification).limit(1)).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "token_address": self.bulk_transfer_token[0],
                "error_transfer_id": [1],
            }

    # <Error_3_2>
    # ~v24.6: Transfer individually
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_3_2(self, processor, db):
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
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        bulk_transfer = BulkTransfer()
        bulk_transfer.issuer_address = _account["address"]
        bulk_transfer.upload_id = self.upload_id_list[0]
        bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer.token_address = self.bulk_transfer_token[0]
        bulk_transfer.from_address = _from_address["address"]
        bulk_transfer.to_address = _to_address["address"]
        bulk_transfer.amount = 1
        bulk_transfer.status = 0  # pending:0
        db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            side_effect=ContractRevertError(code_msg="120601"),
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            await processor.process()

            # Assertion
            _bulk_transfer_upload = db.scalars(
                select(BulkTransferUpload)
                .where(BulkTransferUpload.upload_id == self.upload_id_list[0])
                .limit(1)
            ).first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.scalars(
                select(BulkTransfer)
                .where(
                    and_(
                        BulkTransfer.upload_id == self.upload_id_list[0],
                        BulkTransfer.token_address == self.bulk_transfer_token[0],
                    )
                )
                .limit(1)
            ).first()
            assert _bulk_transfer.status == 2
            assert _bulk_transfer.transaction_error_code == 120601
            assert (
                _bulk_transfer.transaction_error_message
                == "Transfer amount is greater than from address balance."
            )

            _notification = db.scalars(select(Notification).limit(1)).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "token_address": self.bulk_transfer_token[0],
                "error_transfer_id": [1],
            }

    # <Error_4_1>
    # v24.9~: Transfer in batch
    # SendTransactionError
    @pytest.mark.asyncio
    async def test_error_4_1(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.token_address = self.bulk_transfer_token[0]
        token.issuer_address = _account["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.bulk_forced_transfer",
            side_effect=SendTransactionError(),
        ):
            await processor.process()

        # Assertion
        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 2

    # <Error_4_2>
    # v24.9~: Transfer in batch
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_4_2(self, processor, db):
        _account = self.account_list[0]
        _from_address = self.account_list[1]
        _to_address = self.account_list[2]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        db.add(account)

        # Prepare data : Token
        token = Token()
        token.type = TokenType.IBET_STRAIGHT_BOND.value
        token.token_address = self.bulk_transfer_token[0]
        token.issuer_address = _account["address"]
        token.abi = {}
        token.tx_hash = ""
        token.version = TokenVersion.V_24_09
        db.add(token)

        # Prepare data : BulkTransferUpload
        bulk_transfer_upload = BulkTransferUpload()
        bulk_transfer_upload.issuer_address = _account["address"]
        bulk_transfer_upload.upload_id = self.upload_id_list[0]
        bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
        bulk_transfer_upload.token_address = self.bulk_transfer_token[0]
        bulk_transfer_upload.status = 0  # pending:0
        db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for _ in range(3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = 0
            db.add(bulk_transfer)

        db.commit()

        # Execute batch
        with patch(
            target="app.model.blockchain.token.IbetStraightBondContract.bulk_forced_transfer",
            side_effect=ContractRevertError(code_msg="120601"),
        ):
            await processor.process()

        # Assertion
        _bulk_transfer_upload = db.scalars(
            select(BulkTransferUpload).order_by(BulkTransferUpload.upload_id)
        ).all()
        assert _bulk_transfer_upload[0].status == 2

        _bulk_transfer_list = db.scalars(
            select(BulkTransfer).where(BulkTransfer.upload_id == self.upload_id_list[0])
        ).all()
        for _bulk_transfer in _bulk_transfer_list:
            assert _bulk_transfer.status == 2

    # <Error_5>
    # Process down after error occurred, Re-run process
    @pytest.mark.asyncio
    async def test_error_5(self, processor, db):
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
            bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer_upload.token_address = self.bulk_transfer_token[i]
            bulk_transfer_upload.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer_upload)

        # Prepare data : BulkTransfer
        for i in range(0, 3):
            bulk_transfer = BulkTransfer()
            bulk_transfer.issuer_address = _account["address"]
            bulk_transfer.upload_id = self.upload_id_list[0]
            bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND.value
            bulk_transfer.token_address = self.bulk_transfer_token[0]
            bulk_transfer.from_address = _from_address["address"]
            bulk_transfer.to_address = _to_address["address"]
            bulk_transfer.amount = 1
            bulk_transfer.status = i  # pending:0, succeeded:1, failed:2
            db.add(bulk_transfer)

        db.commit()

        # mock
        IbetStraightBondContract_transfer = patch(
            target="app.model.blockchain.token.IbetStraightBondContract.forced_transfer",
            return_value=None,
        )

        with IbetStraightBondContract_transfer:
            # Execute batch
            await processor.process()

            # Assertion
            _bulk_transfer_upload = db.scalars(
                select(BulkTransferUpload)
                .where(BulkTransferUpload.upload_id == self.upload_id_list[0])
                .limit(1)
            ).first()
            assert _bulk_transfer_upload.status == 2

            _bulk_transfer = db.scalars(
                select(BulkTransfer)
                .where(
                    and_(
                        BulkTransfer.upload_id == self.upload_id_list[0],
                        BulkTransfer.token_address == self.bulk_transfer_token[0],
                    )
                )
                .limit(1)
            ).first()
            assert _bulk_transfer.status == 1

            _notification = db.scalars(select(Notification).limit(1)).first()
            assert _notification.id == 1
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert _notification.type == NotificationType.BULK_TRANSFER_ERROR
            assert _notification.code == 2
            assert _notification.metainfo == {
                "upload_id": self.upload_id_list[0],
                "token_type": TokenType.IBET_STRAIGHT_BOND.value,
                "token_address": self.bulk_transfer_token[0],
                "error_transfer_id": [3],
            }
