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
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
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
    IDXTransferApproval,
    IDXTransferApprovalBlockNumber,
    Notification,
    NotificationType
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
import batch_log

process_name = "INDEXER-TransferApproval"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

"""
Batch process for indexing security token transfer approval events

ibetSecurityToken
  - ApplyForTransfer
  - CancelTransfer
  - ApproveTransfer

ibetSecurityTokenEscrow
  - ApplyForTransfer
  - CancelTransfer
  - ApproveTransfer

"""


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_transfer_approval(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_transfer_approval(*args, **kwargs)

    def on_info_notification(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_info_notification(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_transfer_approval(self, event_type: str,
                             token_address: str,
                             exchange_address: str,
                             application_id: int,
                             from_address: Optional[str] = None,
                             to_address: Optional[str] = None,
                             amount: Optional[int] = None,
                             optional_data_applicant: Optional[str] = None,
                             optional_data_approver: Optional[str] = None,
                             block_timestamp: Optional[int] = None):
        """Update Transfer Approval data in DB

        :param event_type: event type [ApplyFor, Cancel, Approve]
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
        transfer_approval = self.db.query(IDXTransferApproval). \
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
        self.db.merge(transfer_approval)

    def on_info_notification(self, issuer_address, code, token_address, id):
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
        self.db.add(notification)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def sync_new_logs(self):
        self.__get_contract_list()

        # Get from_block_number and to_block_number for contract event filter
        idx_transfer_approval_block_number = self.__get_idx_transfer_approval_block_number()
        latest_block = web3.eth.blockNumber

        if idx_transfer_approval_block_number >= latest_block:
            LOG.debug("skip process")
            pass
        else:
            self.__sync_all(idx_transfer_approval_block_number + 1, latest_block)

    @staticmethod
    def get_block_timestamp(event) -> datetime:
        block_timestamp = web3.eth.getBlock(event["blockNumber"])["timestamp"]
        return block_timestamp

    def __get_contract_list(self):
        self.token_list = []
        self.exchange_list = []
        _exchange_list_tmp = []
        issued_token_list = self.db.query(Token). \
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

    def __get_idx_transfer_approval_block_number(self):
        _idx_transfer_approval_block_number = self.db.query(IDXTransferApprovalBlockNumber). \
            first()
        if _idx_transfer_approval_block_number is None:
            return 0
        else:
            return _idx_transfer_approval_block_number.latest_block_number

    def __set_idx_transfer_approval_block_number(self, block_number: int):
        _idx_transfer_approval_block_number = self.db.query(IDXTransferApprovalBlockNumber). \
            first()
        if _idx_transfer_approval_block_number is None:
            _idx_transfer_approval_block_number = IDXTransferApprovalBlockNumber()

        _idx_transfer_approval_block_number.latest_block_number = block_number
        self.db.merge(_idx_transfer_approval_block_number)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_token_apply_for_transfer(block_from, block_to)
        self.__sync_token_cancel_transfer(block_from, block_to)
        self.__sync_token_approve_transfer(block_from, block_to)
        self.__sync_exchange_apply_for_transfer(block_from, block_to)
        self.__sync_exchange_cancel_transfer(block_from, block_to)
        self.__sync_exchange_approve_transfer(block_from, block_to)
        self.__set_idx_transfer_approval_block_number(block_to)
        self.sink.flush()

    def __sync_token_apply_for_transfer(self, block_from, block_to):
        """Sync ApplyForTransfer Events of Tokens

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
                        block_timestamp = self.get_block_timestamp(event=event)
                        self.sink.on_transfer_approval(
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
                            transaction_hash=event["transactionHash"],
                            token_address=token.address,
                            exchange_address=None,
                            application_id=args.get("index"),
                            notice_code=0
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_token_cancel_transfer(self, block_from, block_to):
        """Sync CancelTransfer Events of Tokens

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
                    self.sink.on_transfer_approval(
                        event_type="Cancel",
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
                    self.__register_notification(
                        transaction_hash=event["transactionHash"],
                        token_address=token.address,
                        exchange_address=None,
                        application_id=args.get("index"),
                        notice_code=1
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_token_approve_transfer(self, block_from, block_to):
        """Sync ApproveTransfer Events of Tokens

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
                    block_timestamp = self.get_block_timestamp(event=event)
                    self.sink.on_transfer_approval(
                        event_type="Approve",
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

    def __sync_exchange_apply_for_transfer(self, block_from, block_to):
        """Sync ApplyForTransfer events of exchanges

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
                        block_timestamp = self.get_block_timestamp(event=event)
                        self.sink.on_transfer_approval(
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
                            transaction_hash=event["transactionHash"],
                            token_address=args.get("token", ZERO_ADDRESS),
                            exchange_address=exchange.address,
                            application_id=args.get("escrowId"),
                            notice_code=0
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_cancel_transfer(self, block_from, block_to):
        """Sync CancelTransfer events of exchanges

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
                    self.sink.on_transfer_approval(
                        event_type="Cancel",
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
                    self.__register_notification(
                        transaction_hash=event["transactionHash"],
                        token_address=args.get("token", ZERO_ADDRESS),
                        exchange_address=exchange.address,
                        application_id=args.get("escrowId"),
                        notice_code=1
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_exchange_approve_transfer(self, block_from, block_to):
        """Sync ApproveTransfer events of exchanges

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
                    block_timestamp = self.get_block_timestamp(event=event)
                    self.sink.on_transfer_approval(
                        event_type="Approve",
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

    def __register_notification(self, transaction_hash, token_address, exchange_address, application_id, notice_code):

        # Get IDXTransferApproval's Sequence Id
        transfer_approval = self.db.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == token_address). \
            filter(IDXTransferApproval.exchange_address == exchange_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if transfer_approval is not None:
            # Get issuer address
            token = self.db.query(Token). \
                filter(Token.token_address == token_address). \
                first()
            sender = web3.eth.getTransaction(transaction_hash)["from"]
            if token is not None and token.issuer_address != sender:
                self.sink.on_info_notification(
                    issuer_address=token.issuer_address,
                    code=notice_code,
                    token_address=token_address,
                    id=transfer_approval.id
                )


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.sync_new_logs()
        except Exception as ex:
            LOG.error(ex)
        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
