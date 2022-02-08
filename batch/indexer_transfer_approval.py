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
from datetime import (
    datetime,
    timezone
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    INDEXER_SYNC_INTERVAL,
    DATABASE_URL,
    ZERO_ADDRESS
)
from app.model.db import (
    Token,
    TokenType,
    AdditionalTokenInfo,
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log

process_name = "INDEXER-TransferApproval"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False)

"""
Batch process for indexing security token transfer approval events

ibetSecurityToken
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - ApproveTransfer: 'Finish'

ibetSecurityTokenEscrow
  - ApplyForTransfer: 'ApplyFor'
  - CancelTransfer: 'Cancel'
  - ApproveTransfer: 'Approve'
  - FinishTransfer: 'Finish'

"""


class Processor:
    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.token_list = []

    def sync_new_logs(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            self.__get_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            idx_transfer_approval_block_number = self.__get_idx_transfer_approval_block_number(db_session=db_session)
            latest_block = web3.eth.blockNumber

            if idx_transfer_approval_block_number >= latest_block:
                LOG.debug("skip process")
                pass
            else:
                self.__sync_all(
                    db_session=db_session,
                    block_from=idx_transfer_approval_block_number + 1,
                    block_to=latest_block
                )
                self.__set_idx_transfer_approval_block_number(
                    db_session=db_session,
                    block_number=latest_block
                )
                db_session.commit()
        finally:
            db_session.close()

    def __get_contract_list(self, db_session: Session):
        self.token_list = []
        self.exchange_list = []
        _exchange_list_tmp = []
        issued_token_list = db_session.query(Token). \
            filter(Token.type.in_([TokenType.IBET_STRAIGHT_BOND, TokenType.IBET_SHARE])). \
            filter(Token.token_status == 1). \
            all()
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)
            tradable_exchange_address = ContractUtils.call_function(
                contract=token_contract,
                function_name="tradableExchange",
                args=(),
                default_returns=ZERO_ADDRESS
            )
            if tradable_exchange_address != ZERO_ADDRESS:
                _exchange_list_tmp.append(tradable_exchange_address)

        # Remove duplicate exchanges from a list
        for _exchange_address in list(set(_exchange_list_tmp)):
            exchange_contract = ContractUtils.get_contract(
                contract_name="IbetSecurityTokenEscrow",
                contract_address=_exchange_address
            )
            self.exchange_list.append(exchange_contract)

    def __get_idx_transfer_approval_block_number(self, db_session: Session):
        _idx_transfer_approval_block_number = db_session.query(IDXTransferApprovalBlockNumber). \
            first()
        if _idx_transfer_approval_block_number is None:
            return 0
        else:
            return _idx_transfer_approval_block_number.latest_block_number

    def __set_idx_transfer_approval_block_number(self, db_session: Session, block_number: int):
        _idx_transfer_approval_block_number = db_session.query(IDXTransferApprovalBlockNumber). \
            first()
        if _idx_transfer_approval_block_number is None:
            _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()

        _idx_transfer_approval_block_number.latest_block_number = block_number
        db_session.merge(_idx_transfer_approval_block_number)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_token_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_token_cancel_transfer(db_session, block_from, block_to)
        self.__sync_token_approve_transfer(db_session, block_from, block_to)
        self.__sync_exchange_apply_for_transfer(db_session, block_from, block_to)
        self.__sync_exchange_cancel_transfer(db_session, block_from, block_to)
        self.__sync_exchange_approve_transfer(db_session, block_from, block_to)
        self.__sync_exchange_finish_transfer(db_session, block_from, block_to)

    def __sync_token_apply_for_transfer(self, db_session: Session, block_from, block_to):
        """Sync ApplyForTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = self.__get_block_timestamp(event=event)
                        self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=token.address,
                            exchange_address=None,
                            application_id=args.get("index"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            amount=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
                        self.__register_notification(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"],
                            token_address=token.address,
                            exchange_address=None,
                            application_id=args.get("index"),
                            notice_code=0
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_token_cancel_transfer(self, db_session: Session, block_from, block_to):
        """Sync CancelTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
                    self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        notice_code=1
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_token_approve_transfer(self, db_session: Session, block_from, block_to):
        """Sync ApproveTransfer Events of Tokens

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for token in self.token_list:
            try:
                events = token.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    block_timestamp = self.__get_block_timestamp(event=event)
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Finish",
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_apply_for_transfer(self, db_session: Session, block_from, block_to):
        """Sync ApplyForTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = exchange.events.ApplyForTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    value = args.get("value", 0)
                    if value > sys.maxsize:  # suppress overflow
                        pass
                    else:
                        block_timestamp = self.__get_block_timestamp(event=event)
                        self.__sink_on_transfer_approval(
                            db_session=db_session,
                            event_type="ApplyFor",
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            amount=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
                        self.__register_notification(
                            db_session=db_session,
                            transaction_hash=event["transactionHash"],
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            notice_code=0
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_cancel_transfer(self, db_session: Session, block_from, block_to):
        """Sync CancelTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = exchange.events.CancelTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Cancel",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
                    self.__register_notification(
                        db_session=db_session,
                        transaction_hash=event["transactionHash"],
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        notice_code=1
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_approve_transfer(self, db_session: Session, block_from, block_to):
        """Sync ApproveTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = exchange.events.ApproveTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Approve",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_finish_transfer(self, db_session: Session, block_from, block_to):
        """Sync FinishTransfer events of exchanges

        :param db_session: database session
        :param block_from: From Block
        :param block_to: To Block
        :return: None
        """
        for exchange in self.exchange_list:
            try:
                events = exchange.events.FinishTransfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event["args"]
                    block_timestamp = self.__get_block_timestamp(event=event)
                    self.__sink_on_transfer_approval(
                        db_session=db_session,
                        event_type="Finish",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
                    )
            except Exception as e:
                LOG.exception(e)

    def __register_notification(self,
                                db_session: Session,
                                transaction_hash,
                                token_address,
                                exchange_address,
                                application_id,
                                notice_code):

        # Get IDXTransferApproval's Sequence Id
        transfer_approval = db_session.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == token_address). \
            filter(IDXTransferApproval.exchange_address == exchange_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if transfer_approval is not None:
            # Get issuer address
            token = db_session.query(Token). \
                filter(Token.token_address == token_address). \
                first()
            sender = web3.eth.getTransaction(transaction_hash)["from"]
            if token is not None and token.issuer_address != sender:
                if notice_code == 0:  # ApplyFor
                    _additional_info = db_session.query(AdditionalTokenInfo). \
                        filter(AdditionalTokenInfo.token_address == token_address). \
                        first()
                    if _additional_info is None or _additional_info.is_manual_transfer_approval is not True:
                        # SKIP Automatic approval
                        return
                self.__sink_on_info_notification(
                    db_session=db_session,
                    issuer_address=token.issuer_address,
                    code=notice_code,
                    token_address=token_address,
                    id=transfer_approval.id
                )

    @staticmethod
    def __get_block_timestamp(event) -> int:
        block_timestamp = web3.eth.getBlock(event["blockNumber"])["timestamp"]
        return block_timestamp

    @staticmethod
    def __sink_on_transfer_approval(db_session: Session,
                                    event_type: str,
                                    token_address: str,
                                    exchange_address: Optional[str],
                                    application_id: int,
                                    from_address: Optional[str] = None,
                                    to_address: Optional[str] = None,
                                    amount: Optional[int] = None,
                                    optional_data_applicant: Optional[str] = None,
                                    optional_data_approver: Optional[str] = None,
                                    block_timestamp: Optional[int] = None):
        """Update Transfer Approval data in DB

        :param db_session: database session
        :param event_type: event type [ApplyFor, Cancel, Approve, Finish]
        :param token_address: token address
        :param exchange_address: exchange address (value is set if the event is from exchange)
        :param application_id: application id
        :param from_address: transfer from
        :param to_address: transfer to
        :param amount: transfer amount
        :param optional_data_applicant: optional data (ApplyForTransfer)
        :param optional_data_approver: optional data (ApproveTransfer)
        :param block_timestamp: block timestamp
        :return: None
        """
        transfer_approval = db_session.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == token_address). \
            filter(IDXTransferApproval.exchange_address == exchange_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if event_type == "ApplyFor":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.exchange_address = exchange_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.amount = amount
            try:
                transfer_approval.application_datetime = datetime.fromtimestamp(
                    float(optional_data_applicant),
                    tz=timezone.utc
                )
            except ValueError:
                transfer_approval.application_datetime = None
            transfer_approval.application_blocktimestamp = datetime.fromtimestamp(
                block_timestamp,
                tz=timezone.utc
            )
        elif event_type == "Cancel":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.exchange_address = exchange_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.cancelled = True
        elif event_type == "Approve":
            if transfer_approval is not None:
                transfer_approval.transfer_approved = True
        elif event_type == "Finish":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
                transfer_approval.exchange_address = exchange_address
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            try:
                transfer_approval.approval_datetime = datetime.fromtimestamp(
                    float(optional_data_approver),
                    tz=timezone.utc
                )
            except ValueError:
                transfer_approval.approval_datetime = None
            transfer_approval.approval_blocktimestamp = datetime.fromtimestamp(
                block_timestamp,
                tz=timezone.utc
            )
            transfer_approval.transfer_approved = True
        db_session.merge(transfer_approval)

    @staticmethod
    def __sink_on_info_notification(db_session: Session,
                                    issuer_address: str,
                                    code: int,
                                    token_address: str,
                                    id: int):
        notification = Notification()
        notification.notice_id = uuid.uuid4()
        notification.issuer_address = issuer_address
        notification.priority = 0  # Low
        notification.type = NotificationType.TRANSFER_APPROVAL_INFO
        notification.code = code
        notification.metainfo = {
            "token_address": token_address,
            "id": id
        }
        db_session.add(notification)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.sync_new_logs()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.error(ex)
        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
