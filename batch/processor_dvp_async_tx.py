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
from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, asc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.exceptions import TimeExhausted

from app.database import BatchAsyncSessionLocal
from app.exceptions import SendTransactionError
from app.model.db import (
    Account,
    DVPAsyncProcess,
    DVPAsyncProcessRevertTxStatus,
    DVPAsyncProcessStatus,
    DVPAsyncProcessStepTxStatus,
    DVPAsyncProcessType,
)
from app.model.ibet.exchange import IbetSecurityTokenDVPNoWait
from app.model.ibet.tx_params.ibet_security_token_dvp import (
    CreateDeliveryParams,
    WithdrawPartialParams,
)
from app.utils.e2ee_utils import E2EEUtils
from app.utils.ibet_contract_utils import AsyncContractUtils
from batch import free_malloc
from batch.utils import batch_log
from batch.utils.signal_handler import setup_signal_handler

"""
[PROCESSOR-DVP-ASYNC-TX]

A processor for asynchronous transaction execution of DVP
"""

process_name = "PROCESSOR-DVP-Async-Tx"
LOG = batch_log.get_logger(process_name=process_name)


class Processor:
    def __init__(self, is_shutdown: Event):
        self.is_shutdown = is_shutdown

    async def process(self):
        db_session = BatchAsyncSessionLocal()
        try:
            LOG.info("Process Start")

            # Send step transaction
            await self.__send_step_tx(db_session)
            # Synchronize step transaction result & Send revert transaction
            await self.__sync_step_tx_result(db_session)
            # Synchronize revert transaction result
            await self.__sync_revert_tx_result(db_session)

            LOG.info("Process End")
        finally:
            await db_session.close()

    async def __send_step_tx(self, db_session: AsyncSession):
        """Send process step transactions"""
        processing_list: Sequence[DVPAsyncProcess] = (
            await db_session.scalars(
                select(DVPAsyncProcess).where(
                    and_(
                        DVPAsyncProcess.process_status
                        == DVPAsyncProcessStatus.PROCESSING,
                        DVPAsyncProcess.step_tx_status.in_(
                            [
                                DVPAsyncProcessStepTxStatus.DONE,  # The transaction in the previous step is complete.
                                DVPAsyncProcessStepTxStatus.RETRY,  # The transaction has failed and needs to be retried.
                            ]
                        ),
                    )
                )
            )
        ).all()
        for record in processing_list:
            LOG.info(f"[SendStepTx] Start: record_id={record.id}")

            if self.is_shutdown.is_set():
                LOG.info(f"[SendStepTx] End: record_id={record.id}")
                return

            # Get issuer's private key
            try:
                issuer_pk = await self.__get_issuers_pk(
                    db_session, record.issuer_address
                )
            except (AccountNotFound, KeyfileDecodingError):
                LOG.warning("[SendStepTx] Failed to get issuer's private key")
                LOG.info(f"[SendStepTx] End: record_id={record.id}")
                continue

            # Send step transaction
            dvp_contract_nw = IbetSecurityTokenDVPNoWait(
                contract_address=record.dvp_contract_address
            )
            try:
                if record.process_type == DVPAsyncProcessType.CREATE_DELIVERY:
                    # 0) Deposit -> 1) CreateDelivery
                    tx_hash = await dvp_contract_nw.create_delivery(
                        data=CreateDeliveryParams(
                            token_address=record.token_address,
                            buyer_address=record.buyer_address,
                            amount=record.amount,
                            agent_address=record.agent_address,
                            data=record.data,
                        ),
                        tx_from=record.issuer_address,
                        private_key=issuer_pk,
                    )
                    record.step = 1
                    record.step_tx_hash = tx_hash
                    record.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
                    await db_session.commit()
                    LOG.info(
                        f"[SendStepTx] Sent transaction: record_id={record.id}, process_type={record.process_type}, step=1"
                    )
                elif (
                    record.process_type == DVPAsyncProcessType.CANCEL_DELIVERY
                    or record.process_type == DVPAsyncProcessType.FINISH_DELIVERY
                    or record.process_type == DVPAsyncProcessType.ABORT_DELIVERY
                ):
                    # 0) CancelDelivery, FinishDelivery, AbortDelivery
                    # -> 1) WithdrawPartial
                    tx_hash = await dvp_contract_nw.withdraw_partial(
                        data=WithdrawPartialParams(
                            token_address=record.token_address,
                            value=record.amount,
                        ),
                        tx_from=record.issuer_address,
                        private_key=issuer_pk,
                    )
                    record.step = 1
                    record.step_tx_hash = tx_hash
                    record.step_tx_status = DVPAsyncProcessStepTxStatus.PENDING
                    await db_session.commit()
                    LOG.info(
                        f"[SendStepTx] Sent transaction: record_id={record.id}, process_type={record.process_type}, step=1"
                    )
            except SendTransactionError:
                LOG.exception(
                    f"[SendStepTx] Failed to send step transaction: record_id={record.id}"
                )

            LOG.info(f"[SendStepTx] End: record_id={record.id}")

    async def __sync_step_tx_result(self, db_session: AsyncSession):
        pending_list: Sequence[DVPAsyncProcess] = (
            await db_session.scalars(
                select(DVPAsyncProcess)
                .where(
                    and_(
                        DVPAsyncProcess.process_status
                        == DVPAsyncProcessStatus.PROCESSING,
                        DVPAsyncProcess.step_tx_status
                        == DVPAsyncProcessStepTxStatus.PENDING,
                    )
                )
                .order_by(asc(DVPAsyncProcess.modified))
            )
        ).all()
        for record in pending_list:
            LOG.info(f"[SyncStepTxResult] Start: record_id={record.id}")

            if self.is_shutdown.is_set():
                LOG.info(f"[SyncStepTxResult] End: record_id={record.id}")
                return

            # Wait for tx receipt
            try:
                tx_receipt = await AsyncContractUtils.wait_for_transaction_receipt(
                    tx_hash=record.step_tx_hash, timeout=1
                )
            except TimeExhausted:
                LOG.info(f"[SyncStepTxResult] End: record_id={record.id}")
                continue

            if tx_receipt["status"] == 0:  # Reverted
                LOG.warning(
                    f"[SyncStepTxResult] Step transaction has been reverted: record_id={record.id}, process_type={record.process_type}, step={record.step}"
                )

                # Get issuer's private key
                try:
                    issuer_pk = await self.__get_issuers_pk(
                        db_session, record.issuer_address
                    )
                except (AccountNotFound, KeyfileDecodingError):
                    LOG.warning("[SyncStepTxResult] Failed to get issuer's private key")
                    LOG.info(f"[SyncStepTxResult] End: record_id={record.id}")
                    continue

                # Send revert transaction
                if record.process_type == DVPAsyncProcessType.CREATE_DELIVERY:
                    # CreateDelivery ->  <Reverted> -> WithdrawPartial
                    dvp_contract_nw = IbetSecurityTokenDVPNoWait(
                        contract_address=record.dvp_contract_address
                    )
                    try:
                        tx_hash = await dvp_contract_nw.withdraw_partial(
                            data=WithdrawPartialParams(
                                token_address=record.token_address,
                                value=record.amount,
                            ),
                            tx_from=record.issuer_address,
                            private_key=issuer_pk,
                        )
                        record.step_tx_status = DVPAsyncProcessStepTxStatus.FAILED
                        record.revert_tx_hash = tx_hash
                        record.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
                        await db_session.commit()
                        LOG.info(
                            f"[SyncStepTxResult] Sent revert transaction: record_id={record.id}, process_type={record.process_type}, step={record.step}"
                        )
                    except SendTransactionError:
                        LOG.exception(
                            f"[SyncStepTxResult] Failed to send revert transaction: record_id={record.id}, process_type={record.process_type}, step={record.step}"
                        )
                else:
                    # <Reverted> -> Retry
                    record.step_tx_hash = None
                    record.step_tx_status = DVPAsyncProcessStepTxStatus.RETRY
                    await db_session.commit()
            else:  # Success
                # <Success> -> Update step tx status
                record.step_tx_status = DVPAsyncProcessStepTxStatus.DONE

                # Determine whether all steps are complete.
                if record.process_type in [
                    DVPAsyncProcessType.CREATE_DELIVERY,
                    DVPAsyncProcessType.CANCEL_DELIVERY,
                    DVPAsyncProcessType.FINISH_DELIVERY,
                    DVPAsyncProcessType.ABORT_DELIVERY,
                ]:
                    if record.step == 1:
                        record.process_status = DVPAsyncProcessStatus.DONE_SUCCESS

                await db_session.commit()

            LOG.info(f"[SyncStepTxResult] End: record_id={record.id}")

    async def __sync_revert_tx_result(self, db_session: AsyncSession):
        pending_list: Sequence[DVPAsyncProcess] = (
            await db_session.scalars(
                select(DVPAsyncProcess)
                .where(
                    and_(
                        DVPAsyncProcess.process_status
                        == DVPAsyncProcessStatus.PROCESSING,
                        DVPAsyncProcess.revert_tx_status
                        == DVPAsyncProcessRevertTxStatus.PENDING,
                    )
                )
                .order_by(asc(DVPAsyncProcess.modified))
            )
        ).all()
        for record in pending_list:
            LOG.info(f"[SyncRevertTxResult] Start: record_id={record.id}")

            if self.is_shutdown.is_set():
                LOG.info(f"[SyncRevertTxResult] End: record_id={record.id}")
                return

            # Wait for tx receipt
            try:
                tx_receipt = await AsyncContractUtils.wait_for_transaction_receipt(
                    tx_hash=record.step_tx_hash, timeout=1
                )
            except TimeExhausted:
                LOG.info(f"[SyncRevertTxResult] End: record_id={record.id}")
                continue

            if tx_receipt["status"] == 0:  # Reverted
                LOG.warning(
                    f"[SyncRevertTxResult] Revert transaction has been reverted: record_id={record.id}, process_type={record.process_type}"
                )
                # Get issuer's private key
                try:
                    issuer_pk = await self.__get_issuers_pk(
                        db_session, record.issuer_address
                    )
                except (AccountNotFound, KeyfileDecodingError):
                    LOG.warning(
                        "[SyncRevertTxResult] Failed to get issuer's private key"
                    )
                    LOG.info(f"[SyncRevertTxResult] End: record_id={record.id}")
                    continue

                if record.process_type == DVPAsyncProcessType.CREATE_DELIVERY:
                    # <Reverted> -> Resend revert transaction
                    dvp_contract_nw = IbetSecurityTokenDVPNoWait(
                        contract_address=record.dvp_contract_address
                    )
                    try:
                        tx_hash = await dvp_contract_nw.withdraw_partial(
                            data=WithdrawPartialParams(
                                token_address=record.token_address,
                                value=record.amount,
                            ),
                            tx_from=record.issuer_address,
                            private_key=issuer_pk,
                        )
                        record.revert_tx_hash = tx_hash
                        record.revert_tx_status = DVPAsyncProcessRevertTxStatus.PENDING
                        await db_session.commit()
                        LOG.info(
                            f"[SyncRevertTxResult] Resent revert transaction: record_id={record.id}, process_type={record.process_type}"
                        )
                    except SendTransactionError:
                        LOG.exception(
                            f"[SyncRevertTxResult] Failed to send revert transaction: record_id={record.id}, process_type={record.process_type}"
                        )
            else:  # Success
                record.process_status = DVPAsyncProcessStatus.DONE_FAILED
                record.revert_tx_status = DVPAsyncProcessRevertTxStatus.DONE
                await db_session.commit()

            LOG.info(f"[SyncRevertTxResult] End: record_id={record.id}")

    @staticmethod
    async def __get_issuers_pk(db_session: AsyncSession, issuer_address):
        """Get issuer's private key"""
        issuer_account: Account | None = (
            await db_session.scalars(
                select(Account).where(Account.issuer_address == issuer_address).limit(1)
            )
        ).first()
        if issuer_account is None:
            raise AccountNotFound

        try:
            issuer_pk = decode_keyfile_json(
                raw_keyfile_json=issuer_account.keyfile,
                password=E2EEUtils.decrypt(issuer_account.eoa_password).encode("utf-8"),
            )
        except:
            raise KeyfileDecodingError from None

        return issuer_pk


class AccountNotFound(Exception):
    pass


class KeyfileDecodingError(Exception):
    pass


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

            for _ in range(10):
                if is_shutdown.is_set():
                    break
                await asyncio.sleep(1)
            free_malloc()
    finally:
        LOG.info("Service is shutdown")


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
