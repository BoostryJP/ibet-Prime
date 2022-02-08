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
from datetime import datetime
from typing import List
import os
import sys
import time

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    DATABASE_URL,
    AUTO_TRANSFER_APPROVAL_INTERVAL
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.db import (
    Account,
    Token,
    AdditionalTokenInfo,
    IDXTransferApproval,
    TransferApprovalHistory
)
from app.model.blockchain import (
    IbetSecurityTokenInterface,
    IbetSecurityTokenEscrow
)
from app.model.schema import (
    IbetSecurityTokenApproveTransfer,
    IbetSecurityTokenCancelTransfer,
    IbetSecurityTokenEscrowApproveTransfer
)
from app.exceptions import (
    SendTransactionError,
    ServiceUnavailableError
)
import batch_log

process_name = "PROCESSOR-Auto-Transfer-Approval"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False)


class Processor:

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            applications_tmp = self.__get_application_list(db_session=db_session)

            applications = []
            for application in applications_tmp:
                transfer_approval_history = self.__get_transfer_approval_history(
                    db_session=db_session,
                    token_address=application.token_address,
                    exchange_address=application.exchange_address,
                    application_id=application.application_id
                )
                if transfer_approval_history is None:
                    applications.append(application)

            for application in applications:
                token = self.__get_token(db_session=db_session, token_address=application.token_address)
                if token is None:
                    LOG.warning(f"token not found: {application.token_address}")
                    continue

                # Skip manually approval
                _additional_info = self.__get_additional_token_info(
                    db_session=db_session,
                    token_address=application.token_address
                )
                if _additional_info is not None and _additional_info.is_manual_transfer_approval is True:
                    continue

                try:
                    _account = db_session.query(Account). \
                        filter(Account.issuer_address == token.issuer_address). \
                        first()
                    if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                        LOG.warning(f"Issuer of token_address:{token.token_address} does not exist")
                        continue
                    keyfile_json = _account.keyfile
                    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                    private_key = decode_keyfile_json(
                        raw_keyfile_json=keyfile_json,
                        password=decrypt_password.encode("utf-8")
                    )
                except Exception as err:
                    LOG.exception(f"Could not get the private key: token_address = {application.token_address}", err)
                    continue

                if application.exchange_address is None:
                    self.__approve_transfer_token(
                        db_session=db_session,
                        application=application,
                        issuer_address=token.issuer_address,
                        private_key=private_key
                    )
                else:
                    self.__approve_transfer_exchange(
                        db_session=db_session,
                        application=application,
                        issuer_address=token.issuer_address,
                        private_key=private_key
                    )
                db_session.commit()
        finally:
            db_session.close()

    def __get_token(self, db_session: Session, token_address: str) -> Token:
        token = db_session.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status == 1). \
            first()
        return token

    def __get_application_list(self, db_session: Session) -> List[IDXTransferApproval]:
        transfer_approval_list = db_session.query(IDXTransferApproval). \
            filter(IDXTransferApproval.cancelled.is_(None)). \
            all()
        return transfer_approval_list

    def __get_transfer_approval_history(self,
                                        db_session: Session,
                                        token_address: str,
                                        exchange_address: str,
                                        application_id: int) -> TransferApprovalHistory:
        transfer_approval_history = db_session.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == token_address). \
            filter(TransferApprovalHistory.exchange_address == exchange_address). \
            filter(TransferApprovalHistory.application_id == application_id). \
            first()
        return transfer_approval_history

    def __get_additional_token_info(self, db_session: Session, token_address: str) -> AdditionalTokenInfo:
        _additional_info = db_session.query(AdditionalTokenInfo). \
            filter(AdditionalTokenInfo.token_address == token_address). \
            first()
        return _additional_info

    def __approve_transfer_token(self,
                                 db_session: Session,
                                 application: IDXTransferApproval,
                                 issuer_address: str,
                                 private_key: str):
        try:
            now = str(datetime.utcnow().timestamp())
            _data = {
                "application_id": application.application_id,
                "data": now
            }
            tx_hash, tx_receipt = IbetSecurityTokenInterface.approve_transfer(
                contract_address=application.token_address,
                data=IbetSecurityTokenApproveTransfer(**_data),
                tx_from=issuer_address,
                private_key=private_key
            )
            if tx_receipt["status"] == 1:  # Success
                result = 1
            else:
                IbetSecurityTokenInterface.cancel_transfer(
                    contract_address=application.token_address,
                    data=IbetSecurityTokenCancelTransfer(**_data),
                    tx_from=issuer_address,
                    private_key=private_key
                )
                result = 2
                LOG.error(f"Transfer was canceled: "
                          f"token_address={application.token_address} "
                          f"exchange_address={application.exchange_address} "
                          f"application_id={application.application_id}")

            self.__sink_on_transfer_approval_history(
                db_session=db_session,
                token_address=application.token_address,
                exchange_address=None,
                application_id=application.application_id,
                result=result
            )
        except SendTransactionError:
            LOG.warning(f"Failed to send transaction: "
                        f"token_address={application.token_address} "
                        f"exchange_address={application.exchange_address} "
                        f"application_id={application.application_id}")

    def __approve_transfer_exchange(self,
                                    db_session: Session,
                                    application: IDXTransferApproval,
                                    issuer_address: str,
                                    private_key: str):
        try:
            now = str(datetime.utcnow().timestamp())
            _data = {
                "escrow_id": application.application_id,
                "data": now
            }
            _escrow = IbetSecurityTokenEscrow(application.exchange_address)
            tx_hash, tx_receipt = _escrow.approve_transfer(
                data=IbetSecurityTokenEscrowApproveTransfer(**_data),
                tx_from=issuer_address,
                private_key=private_key
            )
            if tx_receipt["status"] == 1:  # Success
                result = 1
            else:
                result = 2
                LOG.error(f"Failed to send transaction: "
                          f"token_address={application.token_address} "
                          f"exchange_address={application.exchange_address} "
                          f"application_id={application.application_id}")

            self.__sink_on_transfer_approval_history(
                db_session=db_session,
                token_address=application.token_address,
                exchange_address=application.exchange_address,
                application_id=application.application_id,
                result=result
            )
        except SendTransactionError:
            LOG.warning(f"Failed to send transaction: "
                        f"token_address={application.token_address} "
                        f"exchange_address={application.exchange_address} "
                        f"application_id={application.application_id}")

    @staticmethod
    def __sink_on_transfer_approval_history(db_session: Session,
                                            token_address: str,
                                            exchange_address: Optional[str],
                                            application_id: int,
                                            result: int):
        transfer_approval_history = TransferApprovalHistory()
        transfer_approval_history.token_address = token_address
        transfer_approval_history.exchange_address = exchange_address
        transfer_approval_history.application_id = application_id
        transfer_approval_history.result = result
        db_session.add(transfer_approval_history)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.error(ex)
        time.sleep(AUTO_TRANSFER_APPROVAL_INTERVAL)


if __name__ == "__main__":
    main()
