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
from typing import Sequence

from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.types import (
    BlockData,
    TxData
)

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    DATABASE_URL,
    CHAIN_ID
)
from app.exceptions import ServiceUnavailableError
from app.model.db import (
    IDXBlockData,
    IDXBlockDataBlockNumber,
    IDXTxData
)
from app.utils.web3_utils import Web3Wrapper
import batch_log

process_name = "INDEXER-BLOCK_TX_DATA"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing Block and Transaction data"""

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def process(self):
        local_session = self.__get_db_session()
        try:
            latest_block = web3.eth.block_number
            from_block = self.__get_indexed_block_number(local_session) + 1

            if from_block > latest_block:
                LOG.info("skip process: from_block > latest_block")
                return

            LOG.info("syncing from={}, to={}".format(from_block, latest_block))
            for block_number in range(from_block, latest_block + 1):
                block_data: BlockData = web3.eth.get_block(block_number, full_transactions=True)

                # Synchronize block data
                block_model = IDXBlockData()
                block_model.number = block_data.get("number")
                block_model.parent_hash = block_data.get("parentHash").hex()
                block_model.sha3_uncles = block_data.get("sha3Uncles").hex()
                block_model.miner = block_data.get("miner")
                block_model.state_root = block_data.get("stateRoot").hex()
                block_model.transactions_root = block_data.get("transactionsRoot").hex()
                block_model.receipts_root = block_data.get("receiptsRoot").hex()
                block_model.logs_bloom = block_data.get("logsBloom").hex()
                block_model.difficulty = block_data.get("difficulty")
                block_model.gas_limit = block_data.get("gasLimit")
                block_model.gas_used = block_data.get("gasUsed")
                block_model.timestamp = block_data.get("timestamp")
                block_model.proof_of_authority_data = block_data.get("proofOfAuthorityData").hex()
                block_model.mix_hash = block_data.get("mixHash").hex()
                block_model.nonce = block_data.get("nonce").hex()
                block_model.hash = block_data.get("hash").hex()
                block_model.size = block_data.get("size")

                transactions: Sequence[TxData] = block_data.get("transactions")
                transaction_hash_list = []
                for transaction in transactions:
                    # Synchronize tx data
                    tx_model = IDXTxData()
                    tx_model.hash = transaction.get("hash").hex()
                    tx_model.block_hash = transaction.get("blockHash").hex()
                    tx_model.block_number = transaction.get("blockNumber")
                    tx_model.transaction_index = transaction.get("transactionIndex")
                    tx_model.from_address = to_checksum_address(transaction.get("from"))
                    tx_model.to_address = to_checksum_address(transaction.get("to")) if transaction.get("to") else None
                    tx_model.input = transaction.get("input")
                    tx_model.gas = transaction.get("gas")
                    tx_model.gas_price = transaction.get("gasPrice")
                    tx_model.value = transaction.get("value")
                    tx_model.nonce = transaction.get("nonce")
                    local_session.add(tx_model)

                    transaction_hash_list.append(transaction.get("hash").hex())

                block_model.transactions = transaction_hash_list
                local_session.add(block_model)

                self.__set_indexed_block_number(local_session, block_number)

                local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise
        finally:
            local_session.close()
        LOG.info("sync process has been completed")

    @staticmethod
    def __get_indexed_block_number(db_session: Session):
        indexed_block_number = (
            db_session.query(IDXBlockDataBlockNumber).
            filter(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID)).
            first()
        )
        if indexed_block_number is None:
            return -1
        else:
            return indexed_block_number.latest_block_number

    @staticmethod
    def __set_indexed_block_number(db_session: Session, block_number: int):
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = str(CHAIN_ID)
        indexed_block_number.latest_block_number = block_number
        db_session.merge(indexed_block_number)


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
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(5)


if __name__ == "__main__":
    main()
