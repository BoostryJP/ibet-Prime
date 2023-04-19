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
import os
import sys
import time
import uuid
from typing import List

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import batch_log

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.blockchain.tx_params.ibet_share import (
    ForceUnlockPrams as IbetShareForceUnlockParams,
)
from app.model.blockchain.tx_params.ibet_straight_bond import (
    ForceUnlockParams as IbetStraightBondForceUnlockParams,
)
from app.model.db import (
    Account,
    BatchForceUnlock,
    BatchForceUnlockUpload,
    Notification,
    NotificationType,
    TokenType,
)
from app.utils.e2ee_utils import E2EEUtils
from config import DATABASE_URL

"""
[PROCESSOR-Batch-Force-Unlock]

Batch processing for force unlock
"""

process_name = "PROCESSOR-Batch-Force-Unlock"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            upload_list: List[BatchForceUnlockUpload] = (
                db_session.query(BatchForceUnlockUpload)
                .filter(BatchForceUnlockUpload.status == 0)
                .all()
            )
            for upload in upload_list:
                LOG.info(f"Process start: batch_id={upload.batch_id}")

                # Get issuer's private key
                issuer_account = (
                    db_session.query(Account)
                    .filter(Account.issuer_address == upload.issuer_address)
                    .first()
                )
                if issuer_account is None:
                    LOG.warning("Issuer account does not exist")
                    self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=1,
                        batch_id=upload.batch_id,
                        error_data_id_list=[],
                    )
                    upload.status = 2
                    batch_data_list: List[BatchForceUnlock] = (
                        db_session.query(BatchForceUnlock)
                        .filter(BatchForceUnlock.batch_id == upload.batch_id)
                        .filter(BatchForceUnlock.status == 0)
                        .all()
                    )
                    for batch_data in batch_data_list:
                        batch_data.status = 2
                    db_session.commit()
                    continue

                try:
                    issuer_pk = decode_keyfile_json(
                        raw_keyfile_json=issuer_account.keyfile,
                        password=E2EEUtils.decrypt(issuer_account.eoa_password).encode(
                            "utf-8"
                        ),
                    )
                except (ValueError, TypeError):
                    LOG.warning("Failed to decode keyfile")
                    self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=2,
                        batch_id=upload.batch_id,
                        error_data_id_list=[],
                    )
                    upload.status = 2
                    batch_data_list: List[BatchForceUnlock] = (
                        db_session.query(BatchForceUnlock)
                        .filter(BatchForceUnlock.batch_id == upload.batch_id)
                        .filter(BatchForceUnlock.status == 0)
                        .all()
                    )
                    for batch_data in batch_data_list:
                        batch_data.status = 2
                    db_session.commit()
                    continue

                # Batch processing
                batch_data_list: List[BatchForceUnlock] = (
                    db_session.query(BatchForceUnlock)
                    .filter(BatchForceUnlock.batch_id == upload.batch_id)
                    .filter(BatchForceUnlock.status == 0)
                    .all()
                )
                for batch_data in batch_data_list:
                    tx_hash = "-"
                    try:
                        if upload.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                            tx_hash = IbetStraightBondContract(
                                upload.token_address
                            ).force_unlock(
                                data=IbetStraightBondForceUnlockParams(
                                    account_address=batch_data.account_address,
                                    lock_address=batch_data.lock_address,
                                    recipient_address=batch_data.recipient_address,
                                    value=batch_data.value,
                                    data="",
                                ),
                                tx_from=upload.issuer_address,
                                private_key=issuer_pk,
                            )
                        elif upload.token_type == TokenType.IBET_SHARE.value:
                            tx_hash = IbetShareContract(
                                upload.token_address
                            ).force_unlock(
                                data=IbetShareForceUnlockParams(
                                    account_address=batch_data.account_address,
                                    lock_address=batch_data.lock_address,
                                    recipient_address=batch_data.recipient_address,
                                    value=batch_data.value,
                                    data="",
                                ),
                                tx_from=upload.issuer_address,
                                private_key=issuer_pk,
                            )
                        LOG.debug(f"Transaction sent successfully: {tx_hash}")
                        batch_data.status = 1
                    except ContractRevertError as e:
                        LOG.warning(
                            f"Transaction reverted: batch_id=<{batch_data.batch_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                        )
                        batch_data.status = 2
                    except SendTransactionError:
                        LOG.warning(f"Failed to send transaction: {tx_hash}")
                        batch_data.status = 2
                    finally:
                        db_session.commit()  # commit for each data

                # Process failed data
                failed_batch_data_list: List[BatchForceUnlock] = (
                    db_session.query(BatchForceUnlock)
                    .filter(BatchForceUnlock.batch_id == upload.batch_id)
                    .filter(BatchForceUnlock.status == 2)
                    .all()
                )

                error_data_id_list = [data.id for data in failed_batch_data_list]
                # 0: Success, 3: failed
                code = 3 if len(error_data_id_list) > 0 else 0
                self.__sink_on_notification(
                    db_session=db_session,
                    issuer_address=upload.issuer_address,
                    token_address=upload.token_address,
                    token_type=upload.token_type,
                    code=code,
                    batch_id=upload.batch_id,
                    error_data_id_list=error_data_id_list,
                )
                # Update to processed
                upload.status = 2 if len(error_data_id_list) > 0 else 1
                db_session.commit()

                LOG.info(f"Process end: batch_id={upload.batch_id}")
        finally:
            db_session.close()

    @staticmethod
    def __sink_on_notification(
        db_session: Session,
        issuer_address: str,
        token_address: str,
        token_type: str,
        code: int,
        batch_id: str,
        error_data_id_list: list[int],
    ):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.code = code
        notification.type = NotificationType.BATCH_FORCE_UNLOCK_PROCESSED
        notification.metainfo = {
            "batch_id": batch_id,
            "error_data_id": error_data_id_list,
            "token_address": token_address,
            "token_type": token_type,
        }
        db_session.add(notification)


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        try:
            processor.process()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(60)


if __name__ == "__main__":
    main()
