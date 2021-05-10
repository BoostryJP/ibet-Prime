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
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    INDEXER_SYNC_INTERVAL,
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    ZERO_ADDRESS
)
from app.model.db import (
    Token,
    TokenType,
    IDXTransferApproval
)
import batch_log

process_name = "INDEXER-TransferApproval"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_transfer_approval(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_transfer_approval(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_transfer_approval(self, event_type: str,
                             token_address: str, application_id: int,
                             from_address: Optional[str] = None,
                             to_address: Optional[str] = None,
                             amount: Optional[int] = None,
                             optional_data_applicant: Optional[str] = None,
                             optional_data_approver: Optional[str] = None,
                             block_timestamp: Optional[int] = None):
        """Update Transfer Approval data in DB

        :param event_type: event type [ApplyFor, Cancel, Approve]
        :param token_address: token address
        :param application_id: application id
        :param from_address: transfer from
        :param to_address: transfer to
        :param value: transfer amount
        :param optional_data_applicant: optional data (ApplyForTransfer)
        :param optional_data_approver: optional data (ApproveTransfer)
        :param block_timestamp: block timestamp
        :return: None
        """
        transfer_approval = self.db.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == token_address). \
            filter(IDXTransferApproval.application_id == application_id). \
            first()
        if event_type == "ApplyFor":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
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
                transfer_approval.application_id = application_id
                transfer_approval.from_address = from_address
                transfer_approval.to_address = to_address
            transfer_approval.cancelled = True
        elif event_type == "Approve":
            if transfer_approval is None:
                transfer_approval = IDXTransferApproval()
                transfer_approval.token_address = token_address
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

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        issued_token_list = self.db.query(Token).\
            filter(Token.type == TokenType.IBET_SHARE).\
            all()
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)

    def initial_sync(self):
        self.get_token_list()
        # synchronize 1,000,000 blocks at a time
        _to_block = 999999
        _from_block = 0
        if self.latest_block > 999999:
            while _to_block < self.latest_block:
                self.__sync_all(_from_block, _to_block)
                _to_block += 1000000
                _from_block += 1000000
            self.__sync_all(_from_block, self.latest_block)
        else:
            self.__sync_all(_from_block, self.latest_block)
        LOG.info(f"<{process_name}> Initial sync has been completed")

    def sync_new_logs(self):
        self.get_token_list()
        block_to = web3.eth.blockNumber
        if self.latest_block >= block_to:
            return
        self.__sync_all(self.latest_block + 1, block_to)
        self.latest_block = block_to

    @staticmethod
    def get_block_timestamp(event) -> datetime:
        block_timestamp = web3.eth.getBlock(event["blockNumber"])["timestamp"]
        return block_timestamp

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_apply_for_transfer(block_from, block_to)
        self.__sync_cancel_transfer(block_from, block_to)
        self.__sync_approve_transfer(block_from, block_to)
        self.sink.flush()

    def __sync_apply_for_transfer(self, block_from, block_to):
        """Sync ApplyForTransfer Events

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
                            application_id=args.get("index"),
                            from_address=args.get("from", ZERO_ADDRESS),
                            to_address=args.get("to", ZERO_ADDRESS),
                            amount=args.get("value"),
                            optional_data_applicant=args.get("data"),
                            block_timestamp=block_timestamp
                        )
            except Exception as e:
                LOG.exception(e)

    def __sync_cancel_transfer(self, block_from, block_to):
        """Sync CancelTransfer Events

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
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                    )
            except Exception as e:
                LOG.exception(e)

    def __sync_approve_transfer(self, block_from, block_to):
        """Sync ApproveTransfer Events

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
                        application_id=args.get("index"),
                        from_address=args.get("from", ZERO_ADDRESS),
                        to_address=args.get("to", ZERO_ADDRESS),
                        optional_data_approver=args.get("data"),
                        block_timestamp=block_timestamp
                    )
            except Exception as e:
                LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    processor.initial_sync()
    while True:
        try:
            processor.sync_new_logs()
        except Exception as ex:
            LOG.error(ex)
        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
