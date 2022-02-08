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
import uuid

from eth_keyfile import decode_keyfile_json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    DATABASE_URL,
    UPDATE_TOKEN_INTERVAL,
    TOKEN_LIST_CONTRACT_ADDRESS
)
from app.utils.contract_utils import ContractUtils
from app.utils.e2ee_utils import E2EEUtils
from app.model.db import (
    Account,
    Token,
    TokenType,
    UpdateToken,
    Notification,
    NotificationType,
    IDXPosition,
    UTXO
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
from app.exceptions import (
    SendTransactionError,
    ServiceUnavailableError
)
import batch_log

process_name = "PROCESSOR-Update-token"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False)


class Processor:

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            _update_token_list = self.__get_update_token_list(db_session=db_session)
            for _update_token in _update_token_list:

                notice_type = ""
                if _update_token.trigger == "Issue":
                    notice_type = NotificationType.ISSUE_ERROR

                # Get issuer's private key
                try:
                    _account = db_session.query(Account). \
                        filter(Account.issuer_address == _update_token.issuer_address). \
                        first()
                    if _account is None:  # If issuer does not exist, update the status of the upload to ERROR
                        LOG.warning(f"Issuer of the event_id:{_update_token.id} does not exist")
                        self.__sink_on_finish_update_process(
                            db_session=db_session,
                            record_id=_update_token.id,
                            status=2
                        )
                        self.__sink_on_error_notification(
                            db_session=db_session,
                            issuer_address=_update_token.issuer_address,
                            notice_type=notice_type,
                            code=0,
                            token_address=_update_token.token_address,
                            token_type=_update_token.type,
                            arguments=_update_token.arguments)
                        db_session.commit()
                        continue
                    keyfile_json = _account.keyfile
                    decrypt_password = E2EEUtils.decrypt(_account.eoa_password)
                    private_key = decode_keyfile_json(
                        raw_keyfile_json=keyfile_json,
                        password=decrypt_password.encode("utf-8")
                    )
                except Exception as err:
                    LOG.exception(f"Could not get the private key of the issuer of id:{_update_token.id}", err)
                    self.__sink_on_finish_update_process(
                        db_session=db_session,
                        record_id=_update_token.id,
                        status=2
                    )
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=1,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments)
                    db_session.commit()
                    continue

                try:
                    # Token Update
                    token_template = ""
                    if _update_token.type == TokenType.IBET_SHARE:
                        _update_data = self.__create_update_data(
                            trigger=_update_token.trigger,
                            token_type=TokenType.IBET_SHARE,
                            arguments=_update_token.arguments
                        )
                        IbetShareContract.update(
                            contract_address=_update_token.token_address,
                            data=_update_data,
                            tx_from=_update_token.issuer_address,
                            private_key=private_key
                        )
                        token_template = TokenType.IBET_SHARE

                    elif _update_token.type == TokenType.IBET_STRAIGHT_BOND:
                        _update_data = self.__create_update_data(
                            trigger=_update_token.trigger,
                            token_type=TokenType.IBET_STRAIGHT_BOND,
                            arguments=_update_token.arguments
                        )
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
                        db_session.add(_position)

                        # Insert issuer's UTXO data
                        _token = db_session.query(Token). \
                            filter(Token.token_address == _update_token.token_address). \
                            first()
                        block = ContractUtils.get_block_by_transaction_hash(_token.tx_hash)
                        _utxo = UTXO()
                        _utxo.transaction_hash = _token.tx_hash
                        _utxo.account_address = _update_token.issuer_address
                        _utxo.token_address = _update_token.token_address
                        _utxo.amount = _update_token.arguments.get("total_supply")
                        _utxo.block_number = block["number"]
                        _utxo.block_timestamp = datetime.utcfromtimestamp(block["timestamp"])
                        db_session.add(_utxo)

                    self.__sink_on_finish_update_process(
                        db_session=db_session,
                        record_id=_update_token.id,
                        status=1
                    )
                except SendTransactionError as tx_err:
                    LOG.warning(f"Failed to send transaction: id=<{_update_token.id}>")
                    LOG.exception(tx_err)
                    self.__sink_on_finish_update_process(
                        db_session=db_session,
                        record_id=_update_token.id,
                        status=2
                    )
                    self.__sink_on_error_notification(
                        db_session=db_session,
                        issuer_address=_update_token.issuer_address,
                        notice_type=notice_type,
                        code=2,
                        token_address=_update_token.token_address,
                        token_type=_update_token.type,
                        arguments=_update_token.arguments)

                db_session.commit()
        finally:
            db_session.close()

    def __get_update_token_list(self, db_session: Session) -> List[UpdateToken]:
        _update_token_list = db_session.query(UpdateToken). \
            filter(UpdateToken.status == 0). \
            order_by(UpdateToken.id). \
            all()
        return _update_token_list

    def __create_update_data(self, trigger, token_type, arguments):
        if trigger == "Issue":
            # NOTE: Items set at the time of issue do not need to be updated.
            if token_type == TokenType.IBET_SHARE:
                update_data = {
                    "tradable_exchange_contract_address": arguments.get("tradable_exchange_contract_address"),
                    "personal_info_contract_address": arguments.get("personal_info_contract_address"),
                    "transferable": arguments.get("transferable"),
                    "status": arguments.get("status"),
                    "is_offering": arguments.get("is_offering"),
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
                    "status": arguments.get("status"),
                    "is_offering": arguments.get("is_offering"),
                    "is_redeemed": arguments.get("is_redeemed"),
                    "tradable_exchange_contract_address": arguments.get("tradable_exchange_contract_address"),
                    "personal_info_contract_address": arguments.get("personal_info_contract_address"),
                    "contact_information": arguments.get("contact_information"),
                    "privacy_policy": arguments.get("privacy_policy"),
                    "transfer_approval_required": arguments.get("transfer_approval_required"),
                }
                return IbetStraightBondUpdate(**update_data)
        return

    @staticmethod
    def __sink_on_finish_update_process(db_session: Session, record_id: int, status: int):

        _update_token = db_session.query(UpdateToken). \
            filter(UpdateToken.id == record_id). \
            first()
        if _update_token is not None:
            _update_token.status = status
            db_session.merge(_update_token)

            if _update_token.trigger == "Issue":
                _token = db_session.query(Token). \
                    filter(Token.token_address == _update_token.token_address). \
                    first()
                if _token is not None:
                    _token.token_status = status
                    db_session.merge(_token)

    @staticmethod
    def __sink_on_error_notification(db_session: Session,
                                     issuer_address: str,
                                     notice_type: str,
                                     code: int,
                                     token_address: str,
                                     token_type: str,
                                     arguments: dict):
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
        db_session.add(notification)


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
        time.sleep(UPDATE_TOKEN_INTERVAL)


if __name__ == "__main__":
    main()
