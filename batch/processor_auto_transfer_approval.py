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
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)

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
from app.exceptions import SendTransactionError
import batch_log

process_name = "PROCESSOR-Auto-Transfer-Approval"
LOG = batch_log.get_logger(process_name=process_name)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_set_status_transfer_approval_history(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_set_status_transfer_approval_history(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_set_status_transfer_approval_history(self,
                                                token_address: str,
                                                exchange_address: str,
                                                application_id: int,
                                                result: int):
        transfer_approval_history = TransferApprovalHistory()
        transfer_approval_history.token_address = token_address
        transfer_approval_history.exchange_address = exchange_address
        transfer_approval_history.application_id = application_id
        transfer_approval_history.result = result
        self.db.add(transfer_approval_history)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db

    def _get_token(self, token_address: str) -> Token:
        token = self.db.query(Token). \
            filter(Token.token_address == token_address). \
            filter(Token.token_status == 1). \
            first()
        return token

    def _get_application_list(self) -> List[IDXTransferApproval]:
        transfer_approval_list = self.db.query(IDXTransferApproval). \
            filter(IDXTransferApproval.cancelled.is_(None)). \
            all()
        return transfer_approval_list

    def _get_transfer_approval_history(self,
                                       token_address: str,
                                       exchange_address: str,
                                       application_id: int) -> TransferApprovalHistory:
        transfer_approval_history = self.db.query(TransferApprovalHistory). \
            filter(TransferApprovalHistory.token_address == token_address). \
            filter(TransferApprovalHistory.exchange_address == exchange_address). \
            filter(TransferApprovalHistory.application_id == application_id). \
            first()
        return transfer_approval_history

    def _get_additional_token_info(self, token_address: str) -> AdditionalTokenInfo:
        _additional_info = self.db.query(AdditionalTokenInfo). \
            filter(AdditionalTokenInfo.token_address == token_address). \
            first()
        return _additional_info

    def process(self):
        applications_tmp = self._get_application_list()

        applications = []
        for application in applications_tmp:
            transfer_approval_history = self._get_transfer_approval_history(
                token_address=application.token_address,
                exchange_address=application.exchange_address,
                application_id=application.application_id
            )
            if transfer_approval_history is None:
                applications.append(application)

        for application in applications:
            token = self._get_token(application.token_address)
            if token is None:
                LOG.warning(f"token not found: {application.token_address}")
                continue

            # Skip manually approval
            _additional_info = self._get_additional_token_info(application.token_address)
            if _additional_info is not None and _additional_info.is_manual_transfer_approval is True:
                continue

            try:
                _account = self.db.query(Account). \
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
                self._approve_transfer_token(
                    application=application,
                    issuer_address=token.issuer_address,
                    private_key=private_key
                )
            else:
                self._approve_transfer_exchange(
                    application=application,
                    issuer_address=token.issuer_address,
                    private_key=private_key
                )

            self.sink.flush()

    def _approve_transfer_token(self, application: IDXTransferApproval, issuer_address: str, private_key: str):
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

            self.sink.on_set_status_transfer_approval_history(
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

    def _approve_transfer_exchange(self, application: IDXTransferApproval, issuer_address: str, private_key: str):
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

            self.sink.on_set_status_transfer_approval_history(
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


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.process()
        except Exception as ex:
            LOG.error(ex)
        time.sleep(AUTO_TRANSFER_APPROVAL_INTERVAL)


if __name__ == "__main__":
    main()
