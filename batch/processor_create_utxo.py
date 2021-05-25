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
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session
)
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from config import (
    DATABASE_URL,
    WEB3_HTTP_PROVIDER,
    ZERO_ADDRESS,
    SYSTEM_LOCALE
)
from app.model.db import (
    UTXO,
    UTXOBlockNumber,
    Token
)
from app.model.blockchain.utils import ContractUtils
import batch_log
from batch.lib import create_ledger

process_name = "PROCESSOR-Create-UTXO"
LOG = batch_log.get_logger(process_name=process_name)

engine = create_engine(DATABASE_URL, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class Sinks:
    def __init__(self):
        self.sinks = []

    def register(self, sink):
        self.sinks.append(sink)

    def on_utxo(self, *args, **kwargs):
        for sink in self.sinks:
            sink.on_utxo(*args, **kwargs)

    def flush(self, *args, **kwargs):
        for sink in self.sinks:
            sink.flush(*args, **kwargs)


class DBSink:
    def __init__(self, db):
        self.db = db

    def on_utxo(self, spent: bool, transaction_hash: str,
                account_address: str, token_address: str, amount: int,
                block_number: int, block_timestamp: datetime):
        if not spent:
            _utxo = self.db.query(UTXO). \
                filter(UTXO.transaction_hash == transaction_hash). \
                first()
            if _utxo is None:
                _utxo = UTXO()
                _utxo.transaction_hash = transaction_hash
                _utxo.account_address = account_address
                _utxo.token_address = token_address
                _utxo.amount = amount
                _utxo.block_number = block_number
                _utxo.block_timestamp = block_timestamp
                self.db.add(_utxo)
        else:
            _utxo_list = self.db.query(UTXO). \
                filter(UTXO.account_address == account_address). \
                filter(UTXO.token_address == token_address). \
                filter(UTXO.amount > 0). \
                order_by(UTXO.block_timestamp). \
                all()
            spend_amount = amount
            for _utxo in _utxo_list:
                utxo_amount = _utxo.amount
                if spend_amount <= 0:
                    pass
                elif _utxo.amount <= spend_amount:
                    _utxo.amount = 0
                    spend_amount = spend_amount - utxo_amount
                    self.db.merge(_utxo)
                else:
                    _utxo.amount = utxo_amount - spend_amount
                    spend_amount = 0
                    self.db.merge(_utxo)

    def flush(self):
        self.db.commit()


class Processor:
    def __init__(self, sink, db):
        self.sink = sink
        self.db = db
        self.token_contract_list = []

    def process(self):
        self.__refresh_token_contract_list()

        # Get from_block_number and to_block_number for contract event filter
        utxo_block_number = self.__get_utxo_block_number()
        latest_block = web3.eth.blockNumber

        if utxo_block_number >= latest_block:
            LOG.debug("skip process")
            pass
        else:
            block_from = utxo_block_number + 1
            LOG.info(f"syncing from={block_from}, to={latest_block}")
            for token_contract in self.token_contract_list:
                self.__process_transfer(token_contract, block_from, latest_block)
            self.__set_utxo_block_number(latest_block)
            self.sink.flush()

    def __refresh_token_contract_list(self):
        self.token_contract_list = []

        # Update token_contract_list to recent
        _token_list = self.db.query(Token). \
            order_by(Token.id). \
            all()
        for _token in _token_list:
            token_contract = ContractUtils.get_contract(
                contract_name=_token.type,
                contract_address=_token.token_address
            )
            self.token_contract_list.append(token_contract)

    def __get_utxo_block_number(self):
        _utxo_block_number = self.db.query(UTXOBlockNumber). \
            first()
        if _utxo_block_number is None:
            return 0
        else:
            return _utxo_block_number.latest_block_number

    def __set_utxo_block_number(self, block_number: int):
        _utxo_block_number = self.db.query(UTXOBlockNumber). \
            first()
        if _utxo_block_number is None:
            _utxo_block_number = UTXOBlockNumber()

        _utxo_block_number.latest_block_number = block_number
        self.db.merge(_utxo_block_number)

    def __process_transfer(self, token_contract, block_from: int, block_to: int):
        try:
            # When a Transfer event occurs
            events = token_contract.events.Transfer.getLogs(
                fromBlock=block_from,
                toBlock=block_to
            )
            for event in events:

                # Get contract event args
                args = event["args"]
                from_account = args.get("from", ZERO_ADDRESS)
                to_account = args.get("to", ZERO_ADDRESS)
                amount = args.get("value")

                transaction_hash = event["transactionHash"].hex()
                block_number = event["blockNumber"]
                block_timestamp = datetime.utcfromtimestamp(web3.eth.get_block(block_number)["timestamp"])  # UTC

                if amount is not None and amount <= sys.maxsize:
                    # Update UTXO（from account）
                    self.sink.on_utxo(
                        spent=True,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=from_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp
                    )

                    # Update UTXO（to account）
                    self.sink.on_utxo(
                        spent=False,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=to_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp
                    )

                    # Other Processing
                    create_ledger.create_ledger(token_contract.address, self.db)
        except Exception as e:
            LOG.exception(e)


_sink = Sinks()
_sink.register(DBSink(db_session))
processor = Processor(sink=_sink, db=db_session)


def main():
    LOG.info("Service started successfully")

    while True:
        try:
            processor.process()
            LOG.debug("Processed")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(10)


if __name__ == "__main__":
    main()
