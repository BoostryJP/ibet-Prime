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

from app.model.db import Account, BulkTransfer, BulkTransferUpload, TokenType
from batch.processor_bulk_transfer import Sinks, DBSink, Processor
from app.model.utils import E2EEUtils
from tests.account_config import config_eth_account

# from unittest import mock


@pytest.fixture(scope='function')
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
    def test_normal_1(self, processor, db):
        # prepare data : Accounts
        for _account in self.account_list:
            account = Account()
            account.issuer_address = _account["address"]
            account.eoa_password = E2EEUtils.encrypt("password")
            account.keyfile = _account["keyfile"]
            db.add(account)

        for i in range(0, 6):
            # prepare data : BulkTransferUpload
            bulk_transfer_upload = BulkTransferUpload()
            bulk_transfer_upload.issuer_address = self.account_list[i % 3]["address"]
            bulk_transfer_upload.upload_id = self.upload_id_list[i]
            if i < 3:
                bulk_transfer_upload.token_type = TokenType.IBET_STRAIGHT_BOND
            else:
                bulk_transfer_upload.token_type = TokenType.IBET_SHARE
            if i % 3 == 0:
                bulk_transfer_upload.status = 1
            else:
                bulk_transfer_upload.status = 0
            db.add(bulk_transfer_upload)

            # prepare data : BulkTransfer
            for j in range(0, 2):
                bulk_transfer = BulkTransfer()
                bulk_transfer.issuer_address = self.account_list[i % 3]["address"]
                bulk_transfer.upload_id = self.upload_id_list[i]
                bulk_transfer.token_type = TokenType.IBET_STRAIGHT_BOND
                bulk_transfer.token_address = self.bulk_transfer_token[i]
                bulk_transfer.from_address = self.account_list[1]["address"]
                bulk_transfer.to_address = self.account_list[2]["address"]
                bulk_transfer.amount = 1 + i
                # bulk_transfer status inconsistency
                if i % 3 == 2 and j == 1:
                    bulk_transfer.status = 2
                else:
                    bulk_transfer.status = 0
                db.add(bulk_transfer)

        # Execute batch
        processor.process()

        # assertion
        _bulk_transfer_upload = db.query(BulkTransferUpload). \
            order_by(BulkTransferUpload.upload_id).all()
        _bulk_transfer = db.query(BulkTransfer). \
            order_by(BulkTransfer.upload_id).all()

        # Upload id[0]: STRAIGHT_BOND do nothing, when upload_id status default 1
        assert _bulk_transfer_upload[0].upload_id == _bulk_transfer[0].upload_id
        assert _bulk_transfer_upload[0].upload_id == _bulk_transfer[1].upload_id
        assert _bulk_transfer_upload[0].status == 1
        assert _bulk_transfer[0].status == 0
        assert _bulk_transfer[1].status == 0

        # Upload id[1]: STRAIGHT_BOND
        assert _bulk_transfer_upload[1].upload_id == _bulk_transfer[2].upload_id
        assert _bulk_transfer_upload[1].upload_id == _bulk_transfer[3].upload_id
        assert _bulk_transfer_upload[1].status == 1
        assert _bulk_transfer[2].status == 1
        assert _bulk_transfer[3].status == 1

        # Upload id[2]: STRAIGHT_BOND
        assert _bulk_transfer_upload[2].upload_id == _bulk_transfer[4].upload_id
        assert _bulk_transfer_upload[2].upload_id == _bulk_transfer[5].upload_id
        assert _bulk_transfer_upload[2].status == 2
        assert _bulk_transfer[4].status == 2
        assert _bulk_transfer[5].status == 1

        # Upload id[3]: SHARE do nothing, when upload_id status default 1
        assert _bulk_transfer_upload[3].upload_id == _bulk_transfer[6].upload_id
        assert _bulk_transfer_upload[3].upload_id == _bulk_transfer[7].upload_id
        assert _bulk_transfer_upload[3].status == 1
        assert _bulk_transfer[6].status == 0
        assert _bulk_transfer[7].status == 0

        # Upload id[4]: SHARE do nothing, when upload_id status default 1
        assert _bulk_transfer_upload[4].upload_id == _bulk_transfer[8].upload_id
        assert _bulk_transfer_upload[4].upload_id == _bulk_transfer[9].upload_id
        assert _bulk_transfer_upload[4].status == 1
        assert _bulk_transfer[8].status == 1
        assert _bulk_transfer[9].status == 1

        # Upload id[5]: SHARE do nothing, when upload_id status default 1
        assert _bulk_transfer_upload[5].upload_id == _bulk_transfer[10].upload_id
        assert _bulk_transfer_upload[5].upload_id == _bulk_transfer[11].upload_id
        assert _bulk_transfer_upload[5].status == 2
        assert _bulk_transfer[10].status == 2
        assert _bulk_transfer[11].status == 1

    ###########################################################################
    # Error Case
    ###########################################################################
