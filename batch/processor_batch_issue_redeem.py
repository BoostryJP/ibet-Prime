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
import time
import uuid
from typing import Sequence

from eth_keyfile import decode_keyfile_json
from sqlalchemy import and_, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.exceptions import ContractRevertError, SendTransactionError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
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
from batch import batch_log
from config import DATABASE_URL

"""
[PROCESSOR-Batch-Issue-Redeem]

Batch processing for additional issuance and redemption
"""

process_name = "PROCESSOR-Batch-Issue-Redeem"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            upload_list: Sequence[BatchIssueRedeemUpload] = db_session.scalars(
                select(BatchIssueRedeemUpload).where(
                    BatchIssueRedeemUpload.processed == False
                )
            ).all()
            for upload in upload_list:
                LOG.info(f"Process start: upload_id={upload.upload_id}")

                # Get issuer's private key
                issuer_account: Account | None = db_session.scalars(
                    select(Account)
                    .where(Account.issuer_address == upload.issuer_address)
                    .limit(1)
                ).first()
                if issuer_account is None:
                    LOG.exception("Issuer account does not exist")
                    self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=1,
                        upload_category=upload.category,
                        upload_id=upload.upload_id,
                        error_data_id_list=[],
                    )
                    upload.processed = True
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
                    LOG.exception("Failed to decode keyfile")
                    self.__sink_on_notification(
                        db_session=db_session,
                        issuer_address=upload.issuer_address,
                        token_address=upload.token_address,
                        token_type=upload.token_type,
                        code=2,
                        upload_category=upload.category,
                        upload_id=upload.upload_id,
                        error_data_id_list=[],
                    )
                    upload.processed = True
                    db_session.commit()
                    continue

                # Batch processing
                batch_data_list: Sequence[BatchIssueRedeem] = db_session.scalars(
                    select(BatchIssueRedeem).where(
                        and_(
                            BatchIssueRedeem.upload_id == upload.upload_id,
                            BatchIssueRedeem.status == 0,
                        )
                    )
                ).all()
                for batch_data in batch_data_list:
                    tx_hash = "-"
                    try:
                        if upload.token_type == TokenType.IBET_STRAIGHT_BOND.value:
                            if (
                                upload.category
                                == BatchIssueRedeemProcessingCategory.ISSUE.value
                            ):
                                tx_hash = IbetStraightBondContract(
                                    upload.token_address
                                ).additional_issue(
                                    data=IbetStraightBondAdditionalIssueParams(
                                        account_address=batch_data.account_address,
                                        amount=batch_data.amount,
                                    ),
                                    tx_from=upload.issuer_address,
                                    private_key=issuer_pk,
                                )
                            elif (
                                upload.category
                                == BatchIssueRedeemProcessingCategory.REDEEM.value
                            ):
                                tx_hash = IbetStraightBondContract(
                                    upload.token_address
                                ).redeem(
                                    data=IbetStraightBondRedeemParams(
                                        account_address=batch_data.account_address,
                                        amount=batch_data.amount,
                                    ),
                                    tx_from=upload.issuer_address,
                                    private_key=issuer_pk,
                                )
                        elif upload.token_type == TokenType.IBET_SHARE.value:
                            if (
                                upload.category
                                == BatchIssueRedeemProcessingCategory.ISSUE.value
                            ):
                                tx_hash = IbetShareContract(
                                    upload.token_address
                                ).additional_issue(
                                    data=IbetShareAdditionalIssueParams(
                                        account_address=batch_data.account_address,
                                        amount=batch_data.amount,
                                    ),
                                    tx_from=upload.issuer_address,
                                    private_key=issuer_pk,
                                )
                            elif (
                                upload.category
                                == BatchIssueRedeemProcessingCategory.REDEEM.value
                            ):
                                tx_hash = IbetShareContract(
                                    upload.token_address
                                ).redeem(
                                    data=IbetShareRedeemParams(
                                        account_address=batch_data.account_address,
                                        amount=batch_data.amount,
                                    ),
                                    tx_from=upload.issuer_address,
                                    private_key=issuer_pk,
                                )
                        LOG.debug(f"Transaction sent successfully: {tx_hash}")
                        batch_data.status = 1
                    except ContractRevertError as e:
                        LOG.warning(
                            f"Transaction reverted: upload_id=<{batch_data.upload_id}> error_code:<{e.code}> error_msg:<{e.message}>"
                        )
                        batch_data.status = 2
                    except SendTransactionError:
                        LOG.warning(f"Failed to send transaction: {tx_hash}")
                        batch_data.status = 2
                    finally:
                        db_session.commit()  # commit for each data

                # Process failed data
                failed_batch_data_list: Sequence[BatchIssueRedeem] = db_session.scalars(
                    select(BatchIssueRedeem).where(
                        and_(
                            BatchIssueRedeem.upload_id == upload.upload_id,
                            BatchIssueRedeem.status == 2,
                        )
                    )
                ).all()

                error_data_id_list = [data.id for data in failed_batch_data_list]
                # 0: Success, 3: failed
                code = 3 if len(error_data_id_list) > 0 else 0
                self.__sink_on_notification(
                    db_session=db_session,
                    issuer_address=upload.issuer_address,
                    token_address=upload.token_address,
                    token_type=upload.token_type,
                    code=code,
                    upload_category=upload.category,
                    upload_id=upload.upload_id,
                    error_data_id_list=error_data_id_list,
                )
                # Update to processed
                upload.processed = True
                db_session.commit()

                LOG.info(f"Process end: upload_id={upload.upload_id}")
        finally:
            db_session.close()

    @staticmethod
    def __sink_on_notification(
        db_session: Session,
        issuer_address: str,
        token_address: str,
        token_type: str,
        upload_category: str,
        code: int,
        upload_id: str,
        error_data_id_list: list[int],
    ):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.code = code
        notification.type = NotificationType.BATCH_ISSUE_REDEEM_PROCESSED
        notification.metainfo = {
            "category": upload_category,
            "upload_id": upload_id,
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
