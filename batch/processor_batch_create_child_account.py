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
import sys
from asyncio import Event
from typing import Sequence

import uvloop
from coincurve import PublicKey
from eth_utils import keccak, to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.model.db import (
    Account,
    ChildAccount,
    IDXPersonalInfo,
    IDXPersonalInfoHistory,
    PersonalInfoDataSource,
    PersonalInfoEventType,
    TmpChildAccountBatchCreate,
)
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler

"""
[PROCESSOR-Batch-Create-Child-Account]

Batch creation of child accounts
"""

process_name = "PROCESSOR-Batch-Create-Child-Account"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self, is_shutdown: Event):
        self.is_shutdown = is_shutdown

    async def process(self):
        db: AsyncSession = BatchAsyncSessionLocal()

        try:
            LOG.info("Process Start")

            _tmp_list: Sequence[TmpChildAccountBatchCreate] = (
                await db.scalars(select(TmpChildAccountBatchCreate))
            ).all()
            for _tmp in _tmp_list:
                if self.is_shutdown.is_set():
                    return

                # Check if the issuer exists
                _account = (
                    await db.scalars(
                        select(Account)
                        .where(Account.issuer_address == _tmp.issuer_address)
                        .limit(1)
                    )
                ).first()
                if _account is None or _account.issuer_public_key is None:
                    LOG.error(f"Issuer account not found: {_tmp.issuer_address}")
                    await db.delete(_tmp)  # delete tmp data
                    await db.commit()
                    continue

                issuer_pk = PublicKey(data=bytes.fromhex(_account.issuer_public_key))

                # Derive the child address
                index_sk = int(_tmp.child_account_index).to_bytes(32)
                index_pk = PublicKey.from_valid_secret(index_sk)

                child_pk = PublicKey.combine_keys([issuer_pk, index_pk])
                child_addr = to_checksum_address(
                    keccak(child_pk.format(compressed=False)[1:])[-20:]
                )

                # Insert child account record and update index
                _child_account = ChildAccount()
                _child_account.issuer_address = _tmp.issuer_address
                _child_account.child_account_index = _tmp.child_account_index
                _child_account.child_account_address = child_addr
                db.add(_child_account)

                # Insert offchain personal information
                _off_personal_info = IDXPersonalInfo()
                _off_personal_info.issuer_address = _tmp.issuer_address
                _off_personal_info.account_address = child_addr
                _off_personal_info.personal_info = _tmp.personal_info
                _off_personal_info.data_source = PersonalInfoDataSource.OFF_CHAIN
                db.add(_off_personal_info)

                # Insert personal information history
                _personal_info_history = IDXPersonalInfoHistory()
                _personal_info_history.issuer_address = _tmp.issuer_address
                _personal_info_history.account_address = child_addr
                _personal_info_history.event_type = PersonalInfoEventType.REGISTER
                _personal_info_history.personal_info = _tmp.personal_info
                db.add(_personal_info_history)

                # Delete tmp data
                await db.delete(_tmp)
                await db.commit()

            LOG.info("Process End")
        finally:
            await db.close()


async def main():
    LOG.info("Service started successfully")

    is_shutdown = asyncio.Event()
    setup_signal_handler(logger=LOG, is_shutdown=is_shutdown)

    processor = Processor(is_shutdown)

    try:
        while not is_shutdown.is_set():
            try:
                await processor.process()
            except SQLAlchemyError as sa_err:
                LOG.error(
                    f"A database error has occurred: code={sa_err.code}\n{sa_err}"
                )
            except Exception as ex:
                LOG.exception(ex)

            await asyncio.sleep(10)
    finally:
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
