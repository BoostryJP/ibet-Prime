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
import logging
from typing import Optional, Sequence
from unittest.mock import patch

import pytest
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.db import (
    Account,
    BatchRegisterPersonalInfo,
    BatchRegisterPersonalInfoUpload,
    BatchRegisterPersonalInfoUploadStatus,
    Notification,
    NotificationType,
    Token,
    TokenType,
    TokenVersion,
)
from app.model.ibet import IbetShareContract
from app.model.ibet.tx_params.ibet_share import (
    UpdateParams as IbetShareUpdateParams,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import ContractUtils
from batch.processor_batch_register_personal_info import LOG, Processor
from tests.account_config import default_eth_account


@pytest.fixture(scope="function")
def processor(async_db, caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("background")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield Processor(worker_num=0, is_shutdown=asyncio.Event())
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessor:
    account_list = [
        {
            "address": default_eth_account("user1")["address"],
            "keyfile": default_eth_account("user1")["keyfile_json"],
        },
        {
            "address": default_eth_account("user2")["address"],
            "keyfile": default_eth_account("user2")["keyfile_json"],
        },
        {
            "address": default_eth_account("user3")["address"],
            "keyfile": default_eth_account("user3")["keyfile_json"],
        },
        {
            "address": default_eth_account("user4")["address"],
            "keyfile": default_eth_account("user4")["keyfile_json"],
        },
        {
            "address": default_eth_account("user5")["address"],
            "keyfile": default_eth_account("user5")["keyfile_json"],
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

    register_personal_info_token = [
        "0xbB4138520af85fAfdDAACc7F0AabfE188334D0ca",
        "0x55e20Fa9F4Fa854Ef06081734872b734c105916b",
        "0x1d2E98AD049e978B08113fD282BD42948F265DDa",
        "0x2413a63D91eb10e1472a18aD4b9628fBE4aac8B8",
        "0x6f9486251F4034C251ecb8Fa0f087CDDb3cDe6d7",
        "0xd40a1F59c29776B164857bA48AF415CeA072aC98",
    ]

    @staticmethod
    async def deploy_share_token_contract(
        address,
        private_key,
        personal_info_contract_address,
        tradable_exchange_contract_address=None,
        transfer_approval_required=None,
    ):
        arguments = [
            "token.name",
            "token.symbol",
            20,
            100,
            3,
            "token.dividend_record_date",
            "token.dividend_payment_date",
            "token.cancellation_date",
            30,
        ]
        share_contract = IbetShareContract()
        token_address, _, _ = await share_contract.create(
            arguments, address, private_key
        )
        await share_contract.update(
            data=IbetShareUpdateParams(
                transferable=True,
                personal_info_contract_address=personal_info_contract_address,
                tradable_exchange_contract_address=tradable_exchange_contract_address,
                transfer_approval_required=transfer_approval_required,
            ),
            tx_from=address,
            private_key=private_key,
        )

        return ContractUtils.get_contract("IbetShare", token_address)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 Batch Task
    @pytest.mark.asyncio
    async def test_normal_1(
        self, processor: Processor, async_db, ibet_personal_info_contract
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value="mock_tx_hash",
        )

        with PersonalInfoContract_register_info as mock:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            mock.assert_not_called()

    # <Normal_2>
    # Multiple upload / Multiple Register
    @pytest.mark.asyncio
    async def test_normal_2(
        self, processor: Processor, async_db, ibet_personal_info_contract
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        # Only record with "pending" status should be processed
        for i in range(0, 6):
            batch_register_upload = BatchRegisterPersonalInfoUpload()
            batch_register_upload.issuer_address = _account["address"]
            batch_register_upload.upload_id = self.upload_id_list[i]
            batch_register_upload.status = [
                s.value for s in BatchRegisterPersonalInfoUploadStatus
            ][i % 3]
            async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        for i in range(0, 3):
            for _ in range(0, 3):
                batch_register = BatchRegisterPersonalInfo()
                batch_register.upload_id = self.upload_id_list[i]
                batch_register.token_address = token_address_1
                batch_register.account_address = self.account_list[i % 5]["address"]
                batch_register.status = 0 % 2
                batch_register.personal_info = {
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                }
                async_db.add(batch_register)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value="mock_tx_hash",
        )

        with PersonalInfoContract_register_info:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            # Assertion
            _batch_register_upload_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload).where(
                        BatchRegisterPersonalInfoUpload.upload_id.in_(
                            [self.upload_id_list[0], self.upload_id_list[4]]
                        )
                    )
                )
            ).all()
            for _upload in _batch_register_upload_list:
                assert (
                    _upload.status == BatchRegisterPersonalInfoUploadStatus.DONE.value
                )

            _batch_register_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfo).where(
                        BatchRegisterPersonalInfo.upload_id.in_(
                            [self.upload_id_list[0], self.upload_id_list[4]]
                        )
                    )
                )
            ).all()
            for _batch_register in _batch_register_list:
                assert _batch_register.status == 1

    # <Normal_3>
    # Skip other thread processed issuer
    @patch(
        "batch.processor_batch_register_personal_info.BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE",
        2,
    )
    @pytest.mark.asyncio
    async def test_normal_3(
        self, processor: Processor, async_db, ibet_personal_info_contract
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )
        _other_issuer = self.account_list[1]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        # Only record with "pending" status should be processed
        for i in range(0, 6):
            batch_register_upload = BatchRegisterPersonalInfoUpload()
            batch_register_upload.issuer_address = (
                _account["address"] if i % 3 == 0 else _other_issuer["address"]
            )
            batch_register_upload.upload_id = self.upload_id_list[i]
            batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
            async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        for i in range(0, 6):
            for _ in range(0, 3):
                batch_register = BatchRegisterPersonalInfo()
                batch_register.upload_id = self.upload_id_list[i]
                batch_register.token_address = token_address_1
                batch_register.account_address = self.account_list[i % 5]["address"]
                batch_register.status = 0
                batch_register.personal_info = {
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                }
                async_db.add(batch_register)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value="mock_tx_hash",
        )
        processing_issuer = patch(
            "batch.processor_batch_register_personal_info.processing_issuer",
            {
                1: {
                    self.upload_id_list[1]: _other_issuer["address"],
                    self.upload_id_list[2]: _other_issuer["address"],
                    self.upload_id_list[4]: _other_issuer["address"],
                    self.upload_id_list[5]: _other_issuer["address"],
                }
            },
        )

        with PersonalInfoContract_register_info, processing_issuer:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            # Assertion
            _batch_register_upload_list: Sequence[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.status
                        == BatchRegisterPersonalInfoUploadStatus.DONE.value
                    )
                    .order_by(BatchRegisterPersonalInfoUpload.created)
                )
            ).all()
            assert len(_batch_register_upload_list) == 2

            assert _batch_register_upload_list[0].issuer_address == _account["address"]
            assert _batch_register_upload_list[1].issuer_address == _account["address"]

            _batch_register_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfo).where(
                        BatchRegisterPersonalInfo.upload_id.in_(
                            [r.upload_id for r in _batch_register_upload_list]
                        )
                    )
                )
            ).all()
            for _batch_register in _batch_register_list:
                assert _batch_register.status == 1

            _batch_register_upload_list: Sequence[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.status
                        == BatchRegisterPersonalInfoUploadStatus.PENDING.value
                    )
                    .order_by(BatchRegisterPersonalInfoUpload.created)
                )
            ).all()
            assert len(_batch_register_upload_list) == 4

            assert (
                _batch_register_upload_list[0].issuer_address
                == _other_issuer["address"]
            )
            assert (
                _batch_register_upload_list[1].issuer_address
                == _other_issuer["address"]
            )
            assert (
                _batch_register_upload_list[2].issuer_address
                == _other_issuer["address"]
            )
            assert (
                _batch_register_upload_list[3].issuer_address
                == _other_issuer["address"]
            )

            _batch_register_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfo).where(
                        BatchRegisterPersonalInfo.upload_id.in_(
                            [r.upload_id for r in _batch_register_upload_list]
                        )
                    )
                )
            ).all()
            for _batch_register in _batch_register_list:
                assert _batch_register.status == 0

    # <Normal_4>
    # other thread processed issuer(all same issuer)
    @patch(
        "batch.processor_batch_register_personal_info.BATCH_REGISTER_PERSONAL_INFO_WORKER_LOT_SIZE",
        2,
    )
    @pytest.mark.asyncio
    async def test_normal_4(
        self, processor: Processor, async_db, ibet_personal_info_contract
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )
        _other_issuer = self.account_list[1]

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        # Only record with "pending" status should be processed
        for i in range(0, 6):
            batch_register_upload = BatchRegisterPersonalInfoUpload()
            batch_register_upload.issuer_address = _account["address"]
            batch_register_upload.upload_id = self.upload_id_list[i]
            batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
            async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        for i in range(0, 6):
            for _ in range(0, 3):
                batch_register = BatchRegisterPersonalInfo()
                batch_register.upload_id = self.upload_id_list[i]
                batch_register.token_address = token_address_1
                batch_register.account_address = self.account_list[i % 5]["address"]
                batch_register.status = 0
                batch_register.personal_info = {
                    "key_manager": "test_value",
                    "name": "test_value",
                    "postal_code": "1000001",
                    "address": "test_value",
                    "email": "test_value@a.test",
                    "birth": "19900101",
                    "is_corporate": True,
                    "tax_category": 3,
                }
                async_db.add(batch_register)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value="mock_tx_hash",
        )
        processing_issuer = patch(
            "batch.processor_batch_register_personal_info.processing_issuer",
            {
                1: {
                    self.upload_id_list[3]: _account["address"],
                    self.upload_id_list[4]: _account["address"],
                    self.upload_id_list[5]: _account["address"],
                }
            },
        )

        with PersonalInfoContract_register_info, processing_issuer:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            # Assertion
            _batch_register_upload_list: Sequence[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.status
                        == BatchRegisterPersonalInfoUploadStatus.DONE.value
                    )
                    .order_by(BatchRegisterPersonalInfoUpload.created)
                )
            ).all()
            assert len(_batch_register_upload_list) == 2

            assert _batch_register_upload_list[0].issuer_address == _account["address"]
            assert _batch_register_upload_list[1].issuer_address == _account["address"]

            _batch_register_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfo).where(
                        BatchRegisterPersonalInfo.upload_id.in_(
                            [r.upload_id for r in _batch_register_upload_list]
                        )
                    )
                )
            ).all()
            for _batch_register in _batch_register_list:
                assert _batch_register.status == 1

            _batch_register_upload_list: Sequence[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.status
                        == BatchRegisterPersonalInfoUploadStatus.PENDING.value
                    )
                    .order_by(BatchRegisterPersonalInfoUpload.created)
                )
            ).all()

            assert len(_batch_register_upload_list) == 4

            assert _batch_register_upload_list[0].issuer_address == _account["address"]
            assert _batch_register_upload_list[1].issuer_address == _account["address"]
            assert _batch_register_upload_list[2].issuer_address == _account["address"]
            assert _batch_register_upload_list[3].issuer_address == _account["address"]

            _batch_register_list = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfo).where(
                        BatchRegisterPersonalInfo.upload_id.in_(
                            [r.upload_id for r in _batch_register_upload_list[0:3]]
                        )
                    )
                )
            ).all()
            for _batch_register in _batch_register_list:
                assert _batch_register.status == 0

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1>
    # 1 Batch Task but no issuer
    @pytest.mark.asyncio
    async def test_error_1(
        self,
        processor: Processor,
        async_db,
        ibet_personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _account["address"]
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.token_address = token_address_1
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
        async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        batch_register = BatchRegisterPersonalInfo()
        batch_register.upload_id = self.upload_id_list[0]
        batch_register.token_address = token_address_1
        batch_register.account_address = self.account_list[0]["address"]
        batch_register.status = 0
        batch_register.personal_info = {
            "key_manager": "test_value",
            "name": "test_value",
            "postal_code": "1000001",
            "address": "test_value",
            "email": "test_value@a.test",
            "birth": "19900101",
            "is_corporate": True,
            "tax_category": 3,
        }
        async_db.add(batch_register)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            return_value="mock_tx_hash",
        )

        with PersonalInfoContract_register_info as mock:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            mock.assert_not_called()

            # Assertion
            _batch_register_upload: Optional[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.issuer_address
                        == _account["address"]
                    )
                    .limit(1)
                )
            ).first()
            assert (
                _batch_register_upload.status
                == BatchRegisterPersonalInfoUploadStatus.FAILED.value
            )

            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Issuer of the upload_id:{_batch_register_upload.upload_id} does not exist",
                )
            )

            _notification_list = (await async_db.scalars(select(Notification))).all()
            for _notification in _notification_list:
                assert _notification.notice_id is not None
                assert _notification.issuer_address == _account["address"]
                assert _notification.priority == 1
                assert (
                    _notification.type
                    == NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
                )
                assert _notification.code == 0
                assert _notification.metainfo == {
                    "upload_id": batch_register_upload.upload_id,
                    "token_address": batch_register_upload.token_address,
                    "error_registration_id": [],
                }

    # <Error_2>
    # fail to get the private key
    @pytest.mark.asyncio
    async def test_error_2(
        self,
        processor: Processor,
        async_db,
        ibet_personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password_ng")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _account["address"]
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.token_address = token_address_1
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
        async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        batch_register_id_list = []
        for i in range(0, 3):
            batch_register = BatchRegisterPersonalInfo()
            batch_register.upload_id = self.upload_id_list[0]
            batch_register.token_address = token_address_1
            batch_register.account_address = self.account_list[i]["address"]
            batch_register.status = 0
            batch_register.personal_info = {
                "key_manager": "test_value",
                "name": "test_value",
                "postal_code": "1000001",
                "address": "test_value",
                "email": "test_value@a.test",
                "birth": "19900101",
                "is_corporate": True,
                "tax_category": 3,
            }
            async_db.add(batch_register)
            await async_db.flush()
            batch_register_id_list.append(batch_register.id)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            side_effect=SendTransactionError(),
        )

        with PersonalInfoContract_register_info:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            # Assertion
            _batch_register_upload: Optional[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.issuer_address
                        == _account["address"]
                    )
                    .limit(1)
                )
            ).first()
            assert (
                _batch_register_upload.status
                == BatchRegisterPersonalInfoUploadStatus.FAILED.value
            )

            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Failed to send transaction: id=<{batch_register_id_list[0]}>",
                )
            )
            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Failed to send transaction: id=<{batch_register_id_list[1]}>",
                )
            )
            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Failed to send transaction: id=<{batch_register_id_list[2]}>",
                )
            )

            _notification_list = (await async_db.scalars(select(Notification))).all()
            for _notification in _notification_list:
                assert _notification.notice_id is not None
                assert _notification.issuer_address == _account["address"]
                assert _notification.priority == 1
                assert (
                    _notification.type
                    == NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
                )
                assert _notification.code == 1
                assert _notification.metainfo == {
                    "upload_id": batch_register_upload.upload_id,
                    "token_address": batch_register_upload.token_address,
                    "error_registration_id": batch_register_id_list,
                }

    # <Error_3>
    # ContractRevertError
    @pytest.mark.asyncio
    async def test_error_3(
        self,
        processor: Processor,
        async_db,
        ibet_personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password_ng")
        account.keyfile = _account["keyfile"]
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _account["address"]
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.token_address = token_address_1
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
        async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        batch_register_id_list = []
        for i in range(0, 3):
            batch_register = BatchRegisterPersonalInfo()
            batch_register.upload_id = self.upload_id_list[0]
            batch_register.token_address = token_address_1
            batch_register.account_address = self.account_list[i]["address"]
            batch_register.status = 0
            batch_register.personal_info = {
                "key_manager": "test_value",
                "name": "test_value",
                "postal_code": "1000001",
                "address": "test_value",
                "email": "test_value@a.test",
                "birth": "19900101",
                "is_corporate": True,
                "tax_category": 3,
            }
            async_db.add(batch_register)
            await async_db.flush()
            batch_register_id_list.append(batch_register.id)

        await async_db.commit()

        # mock
        PersonalInfoContract_register_info = patch(
            target="app.model.ibet.personal_info.PersonalInfoContract.register_info",
            side_effect=ContractRevertError("999999"),
        )

        with PersonalInfoContract_register_info:
            # Execute batch
            await processor.process()
            async_db.expire_all()

            # Assertion
            _batch_register_upload: Optional[BatchRegisterPersonalInfoUpload] = (
                await async_db.scalars(
                    select(BatchRegisterPersonalInfoUpload)
                    .where(
                        BatchRegisterPersonalInfoUpload.issuer_address
                        == _account["address"]
                    )
                    .limit(1)
                )
            ).first()
            assert (
                _batch_register_upload.status
                == BatchRegisterPersonalInfoUploadStatus.FAILED.value
            )

            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Transaction reverted: id=<{batch_register_id_list[0]}> error_code:<999999> error_msg:<>",
                )
            )
            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Transaction reverted: id=<{batch_register_id_list[1]}> error_code:<999999> error_msg:<>",
                )
            )
            assert 1 == caplog.record_tuples.count(
                (
                    LOG.name,
                    logging.WARN,
                    f"Transaction reverted: id=<{batch_register_id_list[2]}> error_code:<999999> error_msg:<>",
                )
            )

            _notification_list = (await async_db.scalars(select(Notification))).all()
            for _notification in _notification_list:
                assert _notification.notice_id is not None
                assert _notification.issuer_address == _account["address"]
                assert _notification.priority == 1
                assert (
                    _notification.type
                    == NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
                )
                assert _notification.code == 1
                assert _notification.metainfo == {
                    "upload_id": batch_register_upload.upload_id,
                    "token_address": batch_register_upload.token_address,
                    "error_registration_id": batch_register_id_list,
                }

    # <Error_4>
    # Personal info exceeds size limit
    @pytest.mark.asyncio
    async def test_error_4(
        self,
        processor: Processor,
        async_db,
        ibet_personal_info_contract,
        caplog: pytest.LogCaptureFixture,
    ):
        _account = self.account_list[0]
        issuer_private_key = decode_keyfile_json(
            raw_keyfile_json=_account["keyfile"], password="password".encode("utf-8")
        )

        # Prepare data : Account
        account = Account()
        account.issuer_address = _account["address"]
        account.eoa_password = E2EEUtils.encrypt("password_ng")
        account.keyfile = _account["keyfile"]
        account.rsa_passphrase = E2EEUtils.encrypt("password")
        account.rsa_public_key = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAvOlb0wLo/vw/FwFys8IX
/DE4pMNLGA/mJoZ6jz0DdQG4JqGnIitzdaPreZK9H75Cfs5yfNJmP7kJixqSNjyz
WFyZ+0Jf+hwaZ6CxIyTp4zm7A0OLdqzsFIdXXHWFF10g3iwd2KkvKeuocD5c/TT8
tuI2MzhLPwCUn/umBlVPswsRucAC67U5gig5KdeKkR6JdfwVO7OpeMX3gJT6A/Ns
YE/ce4vvF/aH7mNmirnCpkfeqEk5ANpw6bdpEGwYXAdxdD3DhIabMxUvrRZp5LEh
E7pl6K6sCvVKAPl5HPtZ5/AL/Kj7iLU88qY+TYE9bSTtWqhGabSlON7bo132EkZn
Y8BnCy4c8ni00hRkxQ8ZdH468DjzaXOtiNlBLGV7BXiMf7zIE3YJD7Xd22g/XKMs
FsL7F45sgez6SBxiVQrk5WuFtLLD08+3ZAYKqaxFmesw1Niqg6mBB1E+ipYOeBlD
xtUxBqY1kHdua48rjTwEBJz6M+X6YUzIaDS/j/GcFehSyBthj099whK629i1OY3A
PhrKAc+Fywn8tNTkjicPHdzDYzUL2STwAzhrbSfIIc2HlZJSks0Fqs+tQ4Iugep6
fdDfFGjZcF3BwH6NA0frWvUW5AhhkJyJZ8IJ4C0UqakBrRLn2rvThvdCPNPWJ/tx
EK7Y4zFFnfKP3WIA3atUbbcCAwEAAQ==
-----END PUBLIC KEY-----"""
        async_db.add(account)

        # Prepare data : Token
        token_contract_1 = await self.deploy_share_token_contract(
            _account["address"], issuer_private_key, ibet_personal_info_contract.address
        )
        token_address_1 = token_contract_1.address
        token_1 = Token()
        token_1.type = TokenType.IBET_SHARE
        token_1.token_address = token_address_1
        token_1.issuer_address = _account["address"]
        token_1.abi = token_contract_1.abi
        token_1.tx_hash = "tx_hash"
        token_1.version = TokenVersion.V_25_06
        async_db.add(token_1)

        # Prepare data : BatchRegisterPersonalInfoUpload
        batch_register_upload = BatchRegisterPersonalInfoUpload()
        batch_register_upload.issuer_address = _account["address"]
        batch_register_upload.upload_id = self.upload_id_list[0]
        batch_register_upload.token_address = token_address_1
        batch_register_upload.status = BatchRegisterPersonalInfoUploadStatus.PENDING
        async_db.add(batch_register_upload)

        # Prepare data : BatchRegisterPersonalInfo
        batch_register_id_list = []
        for i in range(0, 3):
            batch_register = BatchRegisterPersonalInfo()
            batch_register.upload_id = self.upload_id_list[0]
            batch_register.token_address = token_address_1
            batch_register.account_address = self.account_list[i]["address"]
            batch_register.status = 0
            batch_register.personal_info = {
                "key_manager": "test_value",
                "name": "test_value",
                "postal_code": "1000001",
                "address": "test_value" * 100,  # Too long value
                "email": "test_value@a.test",
                "birth": "19900101",
                "is_corporate": True,
                "tax_category": 3,
            }
            async_db.add(batch_register)
            await async_db.flush()
            batch_register_id_list.append(batch_register.id)

        await async_db.commit()

        # Execute batch
        await processor.process()
        async_db.expire_all()

        # Assertion
        _batch_register_upload: Optional[BatchRegisterPersonalInfoUpload] = (
            await async_db.scalars(
                select(BatchRegisterPersonalInfoUpload)
                .where(
                    BatchRegisterPersonalInfoUpload.issuer_address
                    == _account["address"]
                )
                .limit(1)
            )
        ).first()
        assert (
            _batch_register_upload.status
            == BatchRegisterPersonalInfoUploadStatus.FAILED.value
        )

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.WARN,
                f"Failed to send transaction: id=<{batch_register_id_list[0]}>",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.WARN,
                f"Failed to send transaction: id=<{batch_register_id_list[1]}>",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.WARN,
                f"Failed to send transaction: id=<{batch_register_id_list[2]}>",
            )
        )

        _notification_list = (await async_db.scalars(select(Notification))).all()
        for _notification in _notification_list:
            assert _notification.notice_id is not None
            assert _notification.issuer_address == _account["address"]
            assert _notification.priority == 1
            assert (
                _notification.type
                == NotificationType.BATCH_REGISTER_PERSONAL_INFO_ERROR
            )
            assert _notification.code == 1
            assert _notification.metainfo == {
                "upload_id": batch_register_upload.upload_id,
                "token_address": batch_register_upload.token_address,
                "error_registration_id": batch_register_id_list,
            }
