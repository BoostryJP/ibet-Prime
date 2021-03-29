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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import WEB3_HTTP_PROVIDER, DATABASE_URL, ZERO_ADDRESS, INDEXER_SYNC_INTERVAL
from app.model.db import Token, TokenType, IDXPosition
import batch_log
process_name = "INDEXER-Position-Share"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, _sink):
        self.sinks.append(_sink)

    def on_position(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_position(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_position(self, token_address: str, account_address: str, balance: int):
        """Update balance data

        :param token_address: token address
        :param account_address: account address
        :param balance: balance
        :return: None
        """
        position = self.db.query(IDXPosition). \
            filter(IDXPosition.token_address == token_address). \
            filter(IDXPosition.account_address == account_address). \
            first()
        if position is None:
            LOG.info(f"Position created (Share): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance
        else:
            position.balance = balance
        self.db.merge(position)

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

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_issuer()
        self.__sync_issue(block_from, block_to)
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.sink.flush()

    def __sync_issuer(self):
        """Synchronize issuer position"""
        for token in self.token_list:
            try:
                issuer_address = token.functions.owner().call()
                balance = token.functions.balanceOf(issuer_address).call()
                self.sink.on_position(
                    token_address=to_checksum_address(token.address),
                    account_address=issuer_address,
                    balance=balance
                )
            except Exception as e:
                LOG.exception(e)

    def __sync_issue(self, block_from: int, block_to: int):
        """Synchronize Issue events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.events.Issue.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)

    def __sync_transfer(self, block_from: int, block_to: int):
        """Synchronize Transfer events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.events.Transfer.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    # from address
                    from_account = args.get("from", ZERO_ADDRESS)
                    from_account_balance = token.functions.balanceOf(from_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=from_account,
                        balance=from_account_balance
                    )
                    # to address
                    to_account = args.get("to", ZERO_ADDRESS)
                    to_account_balance = token.functions.balanceOf(to_account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=to_account,
                        balance=to_account_balance,
                    )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)

    def __sync_lock(self, block_from: int, block_to: int):
        """Synchronize Lock events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.events.Lock.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)

    def __sync_unlock(self, block_from: int, block_to: int):
        """Synchronize Unlock events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.events.Unlock.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("to", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)

    def __sync_redeem(self, block_from: int, block_to: int):
        """Synchronize Redeem events

        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list:
            try:
                event_filter = token.events.Redeem.createFilter(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in event_filter.get_all_entries():
                    args = event["args"]
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
                web3.eth.uninstallFilter(event_filter.filter_id)
            except Exception as e:
                LOG.exception(e)

_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(_sink, db_session)
LOG.info("Service started successfully")

processor.initial_sync()
while True:
    processor.sync_new_logs()
    time.sleep(INDEXER_SYNC_INTERVAL)
