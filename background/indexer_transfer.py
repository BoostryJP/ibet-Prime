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
import logging
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), "JST")

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import INDEXER_SYNC_INTERVAL, WEB3_HTTP_PROVIDER, DATABASE_URL
from app.model.db import Token, EventTransfer

from web3 import Web3
from web3.middleware import geth_poa_middleware

log_fmt = "[%(asctime)s] [INDEXER-Transfer] [%(process)d] [%(levelname)s] %(message)s"
logging.basicConfig(format=log_fmt, level=logging.INFO)

# 初期化
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

    def on_transfer(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_transfer(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_transfer(self, transaction_hash, token_address,
                    transfer_from, transfer_to, amount, block_timestamp):
        transfer_record = self.__get_record(transaction_hash, token_address)
        if transfer_record is None:
            transfer_record = EventTransfer()
            transfer_record.transaction_hash = transaction_hash
            transfer_record.token_address = token_address
            transfer_record.transfer_from = transfer_from
            transfer_record.transfer_to = transfer_to
            transfer_record.amount = amount
            transfer_record.block_timestamp = block_timestamp
            self.db.merge(transfer_record)
            logging.info(f"Transfer: transaction_hash={transaction_hash}")

    def flush(self):
        self.db.commit()

    def __get_record(self, transaction_hash, token_address):
        return self.db.query(EventTransfer). \
            filter(EventTransfer.transaction_hash == transaction_hash). \
            filter(EventTransfer.token_address == token_address). \
            first()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.latest_block = web3.eth.blockNumber
        self.db = db
        self.token_list = []

    def get_token_list(self):
        self.token_list = []
        issued_token_list = self.db.query(Token).all()
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)

    def initial_sync(self):
        self.get_token_list()
        # 1,000,000ブロックずつ同期処理を行う
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

    def sync_new_logs(self):
        self.get_token_list()
        blockTo = web3.eth.blockNumber
        if blockTo == self.latest_block:
            return
        self.__sync_all(self.latest_block + 1, blockTo)
        self.latest_block = blockTo

    def __sync_all(self, block_from, block_to):
        logging.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_transfer(block_from, block_to)
        self.sink.flush()

    def __sync_transfer(self, block_from, block_to):
        for token in self.token_list:
            try:
                event_filter = token.events.Transfer.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    transaction_hash = event["transactionHash"].hex()
                    block_timestamp = datetime.fromtimestamp(web3.eth.getBlock(event["blockNumber"])["timestamp"], JST)
                    if args["value"] > sys.maxsize:
                        pass
                    else:
                        self.sink.on_transfer(
                            transaction_hash=transaction_hash,
                            token_address=to_checksum_address(token.address),
                            transfer_from=args["from"],
                            transfer_to=args["to"],
                            amount=args["value"],
                            block_timestamp=block_timestamp
                        )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                logging.error(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(INDEXER_SYNC_INTERVAL)
