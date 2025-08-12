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
import json
import sys
from typing import Sequence

import uvloop
from eth_keyfile import decode_keyfile_json
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ContractRevertError
from app.model.db import (
    Account,
    EthToIbetBridgeTx,
    EthToIbetBridgeTxStatus,
    EthToIbetBridgeTxType,
    IbetBridgeTxParamsForceChangeLockedAccount,
    IbetBridgeTxParamsForceUnlock,
)
from app.model.ibet import IbetSecurityTokenInterface
from app.model.ibet.tx_params.ibet_security_token import (
    ForceChangeLockedAccountParams,
    ForceUnlockParams,
)
from app.utils.e2ee_utils import E2EEUtils
from batch import free_malloc
from batch.utils import batch_log
from config import IBET_WST_BRIDGE_INTERVAL

"""
[PROCESSOR-ETH-WST-Bridge-To-Ibet]

This processor sends bridge transactions for ibetfin.
"""

process_name = "PROCESSOR-ETH-WST-Bridge-To-Ibet"
LOG = batch_log.get_logger(process_name=process_name)


class WSTBridgeToIbetProcessor:
    """
    Processor to send Bridge transactions for ibetfin.
    """

    @staticmethod
    async def send_ibet_tx():
        """
        Send ibet bridge transactions.
        """
        db_session: AsyncSession = BatchAsyncSessionLocal()
        try:
            pending_tx_list: Sequence[EthToIbetBridgeTx] = (
                await db_session.scalars(
                    select(EthToIbetBridgeTx).where(
                        EthToIbetBridgeTx.status == EthToIbetBridgeTxStatus.PENDING
                    )
                )
            ).all()
            for pending_tx in pending_tx_list:
                LOG.info(
                    f"Sending ibet bridge transaction: id={pending_tx.tx_id}, type={pending_tx.tx_type}"
                )
                # Get the issuer's private key
                issuer: Account | None = (
                    await db_session.scalars(
                        select(Account)
                        .where(Account.issuer_address == pending_tx.tx_sender)
                        .limit(1)
                    )
                ).first()
                if issuer is None:
                    LOG.warning(
                        f"Cannot find issuer for transaction: id={pending_tx.tx_id}"
                    )
                    continue

                issuer_pk = decode_keyfile_json(
                    raw_keyfile_json=issuer.keyfile,
                    password=E2EEUtils.decrypt(issuer.eoa_password).encode("utf-8"),
                )

                ibet_token_contract = IbetSecurityTokenInterface(
                    pending_tx.token_address
                )

                try:
                    # Depending on the transaction type, call the appropriate method
                    if pending_tx.tx_type == EthToIbetBridgeTxType.FORCE_UNLOCK:
                        tx_params: IbetBridgeTxParamsForceUnlock = pending_tx.tx_params
                        tx_hash, tx_receipt = await ibet_token_contract.force_unlock(
                            tx_params=ForceUnlockParams(
                                lock_address=tx_params["lock_address"],
                                account_address=tx_params["account_address"],
                                recipient_address=tx_params["recipient_address"],
                                value=tx_params["value"],
                                data=json.dumps(tx_params["data"]),
                            ),
                            tx_sender=pending_tx.tx_sender,
                            tx_sender_key=issuer_pk,
                        )
                    elif (
                        pending_tx.tx_type
                        == EthToIbetBridgeTxType.FORCE_CHANGE_LOCKED_ACCOUNT
                    ):
                        tx_params: IbetBridgeTxParamsForceChangeLockedAccount = (
                            pending_tx.tx_params
                        )
                        (
                            tx_hash,
                            tx_receipt,
                        ) = await ibet_token_contract.force_change_locked_account(
                            tx_params=ForceChangeLockedAccountParams(
                                lock_address=tx_params["lock_address"],
                                before_account_address=tx_params[
                                    "before_account_address"
                                ],
                                after_account_address=tx_params[
                                    "after_account_address"
                                ],
                                value=tx_params["value"],
                                data=json.dumps(tx_params["data"]),
                            ),
                            tx_sender=pending_tx.tx_sender,
                            tx_sender_key=issuer_pk,
                        )
                    else:
                        LOG.error(
                            f"Unknown transaction type: id={pending_tx.tx_id}, type={pending_tx.tx_type}"
                        )
                        pending_tx.status = EthToIbetBridgeTxStatus.FAILED
                        await db_session.merge(pending_tx)
                        await db_session.commit()
                        continue
                except ContractRevertError as cre:
                    # If the transaction failed, update the status to FAILED
                    LOG.error(
                        f"Transaction failed: id={pending_tx.tx_id} ( {cre.code} | {cre.message} )"
                    )
                    pending_tx.status = EthToIbetBridgeTxStatus.FAILED
                    await db_session.merge(pending_tx)
                    await db_session.commit()
                    continue

                # If the transaction succeeded, update the status to SUCCEEDED
                LOG.info(f"Transaction sent successfully: id={pending_tx.tx_id}")
                pending_tx.tx_hash = tx_hash
                pending_tx.block_number = tx_receipt["blockNumber"]
                pending_tx.status = EthToIbetBridgeTxStatus.SUCCEEDED
                await db_session.merge(pending_tx)
                await db_session.commit()
        except Exception:
            # If another error occurs, retry the transaction later
            await db_session.rollback()
            raise
        finally:
            await db_session.close()


async def main():
    LOG.info("Service started successfully")
    bridge_tx_processor = WSTBridgeToIbetProcessor()

    while True:
        try:
            await bridge_tx_processor.send_ibet_tx()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during processing")

        await asyncio.sleep(IBET_WST_BRIDGE_INTERVAL)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
