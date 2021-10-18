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
from typing import List
import os
import sys
import time
import uuid

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
    UPDATE_TOKEN_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS
)
from app.utils.e2ee_utils import E2EEUtils
from app.model.db import (
    Account,
    Token,
    TokenType,
    UpdateToken,
    Notification,
    NotificationType,
    IDXPosition
)
from app.model.blockchain import (
    IbetStraightBondContract,
    IbetShareContract,
    TokenListContract
)
from app.model.schema import (
    IbetShareUpdate,
    IbetStraightBondUpdate
)
from app.exceptions import SendTransactionError
import batch_log

process_name = "PROCESSOR-Update-token"
LOG = batch_log.get_logger(process_name=process_name)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_finish_update_process(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_finish_update_process(*args, **kwargs)

    def on_error_notification(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_error_notification(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_finish_update_process(self, record_id, status):

        _update_token = self.db.query(UpdateToken). \
            filter(UpdateToken.id == record_id). \
            first()
        if _update_token is not None:
            _update_token.status = status
            self.db.merge(_update_token)

            if _update_token.trigger == "Issue":
                _token = self.db.query(Token). \
                    filter(Token.token_address == _update_token.token_address). \
                    first()
                if _token is not None:
                    _token.token_status = status
                    self.db.merge(_token)

    def on_error_notification(self, issuer_address, notice_type, code, token_address, token_type, arguments):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 1  # Medium
        notification.type = notice_type
        notification.code = code
        notification.metainfo = {
            "token_address": token_address,
            "token_type": token_type,
            "arguments": arguments
        }
        self.db.add(notification)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db

    def _get_update_token_list(self) -> List[UpdateToken]:
        _update_token_list = self.db.query(UpdateToken). \
            filter(UpdateToken.status == 0). \
            order_by(UpdateToken.id). \
            all()
        return _update_token_list

    def _create_update_data(self, trigger, token_type, arguments):
        if trigger == "Issue":
            # NOTE: Items set at the time of issue do not need to be updated.
            if token_type == TokenType.IBET_SHARE:
                update_data = {
                    "tradable_exchange_contract_address": arguments.get("tradable_exchange_contract_address"),
                    "personal_info_contract_address": arguments.get("personal_info_contract_address"),
                    "image_url": arguments.get("image_url"),
                    "transferable": arguments.get("transferable"),
                    "status": arguments.get("status"),
                    "offering_status": arguments.get("offering_status"),
                    "contact_information": arguments.get("contact_information"),
                    "privacy_policy": arguments.get("privacy_policy"),
                    "transfer_approval_required": arguments.get("transfer_approval_required"),
                    "is_canceled": arguments.get("is_canceled")
                }
                return IbetShareUpdate(**update_data)
            elif token_type == TokenType.IBET_STRAIGHT_BOND:
                update_data = {
                    "interest_rate": arguments.get("interest_rate"),
                    "interest_payment_date": arguments.get("interest_payment_date"),
                    "transferable": arguments.get("transferable"),
                    "image_url": arguments.get("image_url"),
                    "status": arguments.get("status"),
                    "initial_offering_status": arguments.get("initial_offering_status"),
                    "is_redeemed": arguments.get("is_redeemed"),
                    "tradable_exchange_contract_address": arguments.get("tradable_exchange_contract_address"),
                    "personal_info_contract_address": arguments.get("personal_info_contract_address"),
                    "contact_information": arguments.get("contact_information"),
                    "privacy_policy": arguments.get("privacy_policy")
                }
                return IbetStraightBondUpdate(**update_data)
        return

    def process(self):
        _update_token_list = self._get_update_token_list()
        for _update_token in _update_token_list:

            notice_type = ""
            if _update_token.trigger == "Issue":
                notice_type = NotificationType.ISSUE_ERROR

            # Get issuer's private key
            try:
                _account = self.db.query(Account). \
                    filter(Account.issuer_address == _update_token.issuer_address). \
                    first()
                if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                    LOG.warning(f"Issuer of the event_id:{_update_token.id} does not exist")
                    self.sink.on_finish_update_process(
                        record_id=_update_token.id,
                        status=2
                    )
                    self.sink.on_error_notification(
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=0,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments)
                    self.sink.flush()
                    continue
                keyfile_json = _account.keyfile
                decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                private_key = decode_keyfile_json(
                    raw_keyfile_json=keyfile_json,
                    password=decrypt_password.encode("utf-8")
                )
            except Exception as err:
                LOG.exception(f"Could not get the private key of the issuer of id:{_update_token.id}", err)
                self.sink.on_finish_update_process(
                    record_id=_update_token.id,
                    status=2
                )
                self.sink.on_error_notification(
                    issuer_address=_update_token.issuer_address,
                    notice_type=notice_type,
                    code=1,
                    token_address=_update_token.token_address,
                    token_type=_update_token.type,
                    arguments=_update_token.arguments)
                self.sink.flush()
                continue

            try:
                # Token Update
                token_template = ""
                if _update_token.type == TokenType.IBET_SHARE:

                    _update_data = \
                        self._create_update_data(_update_token.trigger, TokenType.IBET_SHARE, _update_token.arguments)
                    IbetShareContract.update(
                        contract_address=_update_token.token_address,
                        data=_update_data,
                        tx_from=_update_token.issuer_address,
                        private_key=private_key
                    )
                    token_template = TokenType.IBET_SHARE

                elif _update_token.type == TokenType.IBET_STRAIGHT_BOND:
                    _update_data = \
                        self._create_update_data(_update_token.trigger, TokenType.IBET_STRAIGHT_BOND,
                                                 _update_token.arguments)
                    IbetStraightBondContract.update(
                        contract_address=_update_token.token_address,
                        data=_update_data,
                        tx_from=_update_token.issuer_address,
                        private_key=private_key
                    )
                    token_template = TokenType.IBET_STRAIGHT_BOND

                if _update_token.trigger == "Issue":

                    # Register token_address token list
                    TokenListContract.register(
                        token_list_address=TOKEN_LIST_CONTRACT_ADDRESS,
                        token_address=_update_token.token_address,
                        token_template=token_template,
                        account_address=_update_token.issuer_address,
                        private_key=private_key
                    )

                    # Insert initial position data
                    _position = IDXPosition()
                    _position.token_address = _update_token.token_address
                    _position.account_address = _update_token.issuer_address
                    _position.balance = _update_token.arguments.get("total_supply")
                    _position.exchange_balance = 0
                    _position.exchange_commitment = 0
                    _position.pending_transfer = 0
                    self.db.add(_position)

                self.sink.on_finish_update_process(
                    record_id=_update_token.id,
                    status=1
                )
            except SendTransactionError as tx_err:
                LOG.warning(f"Failed to send transaction: id=<{_update_token.id}>")
                LOG.exception(tx_err)
                self.sink.on_finish_update_process(
                    record_id=_update_token.id,
                    status=2
                )
                self.sink.on_error_notification(
                    issuer_address=_update_token.issuer_address,
                    notice_type=notice_type,
                    code=2,
                    token_address=_update_token.token_address,
                    token_type=_update_token.type,
                    arguments=_update_token.arguments)

            self.sink.flush()


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
        time.sleep(UPDATE_TOKEN_INTERVAL)


if __name__ == "__main__":
    main()
