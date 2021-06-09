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
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import (
    WEB3_HTTP_PROVIDER,
    DATABASE_URL,
    ZERO_ADDRESS,
    INDEXER_SYNC_INTERVAL
)
from app.model.db import (
    Token,
    TokenType,
    IDXPosition,
    IDXPositionBondBlockNumber
)
import batch_log

process_name = "INDEXER-Position-Bond"
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
            LOG.debug(f"Position created (Bond): token_address={token_address}, account_address={account_address}")
            position = IDXPosition()
            position.token_address = token_address
            position.account_address = account_address
            position.balance = balance
            position.pending_transfer = 0
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

    def sync_new_logs(self):
        self.__get_token_list()

        # Get from_block_number and to_block_number for contract event filter
        idx_position_block_number = self.__get_idx_position_block_number()
        latest_block = web3.eth.blockNumber

        if idx_position_block_number >= latest_block:
            LOG.debug("skip process")
            pass
        else:
            self.__sync_all(idx_position_block_number + 1, latest_block)

    def __get_token_list(self):
        self.token_list = []
        issued_token_list = self.db.query(Token). \
            filter(Token.type == TokenType.IBET_STRAIGHT_BOND). \
            filter(Token.token_status == 1). \
            all()
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)

    def __get_idx_position_block_number(self):
        _idx_position_block_number = self.db.query(IDXPositionBondBlockNumber). \
            first()
        if _idx_position_block_number is None:
            return 0
        else:
            return _idx_position_block_number.latest_block_number

    def __set_idx_position_block_number(self, block_number: int):
        _idx_position_block_number = self.db.query(IDXPositionBondBlockNumber). \
            first()
        if _idx_position_block_number is None:
            _idx_position_block_number = IDXPositionBondBlockNumber()

        _idx_position_block_number.latest_block_number = block_number
        self.db.merge(_idx_position_block_number)

    def __sync_all(self, block_from: int, block_to: int):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))
        self.__sync_issuer()
        self.__sync_issue(block_from, block_to)
        self.__sync_transfer(block_from, block_to)
        self.__sync_lock(block_from, block_to)
        self.__sync_unlock(block_from, block_to)
        self.__set_idx_position_block_number(block_to)
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
                events = token.events.Issue.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("target_address", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
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
                events = token.events.Transfer.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
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
                events = token.events.Lock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("from", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
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
                events = token.events.Unlock.getLogs(
                    fromBlock=block_from,
                    toBlock=block_to
                )
                for event in events:
                    args = event['args']
                    account = args.get("to", ZERO_ADDRESS)
                    balance = token.functions.balanceOf(account).call()
                    self.sink.on_position(
                        token_address=to_checksum_address(token.address),
                        account_address=account,
                        balance=balance
                    )
            except Exception as e:
                LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
