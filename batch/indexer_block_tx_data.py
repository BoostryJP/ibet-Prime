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

import asyncio
import sys
from typing import Sequence

import uvloop
from eth_utils import to_checksum_address
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.types import BlockData, TxData

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.db import IDXBlockData, IDXBlockDataBlockNumber, IDXTxData
from app.utils.ibet_web3_utils import AsyncWeb3Wrapper
from batch import free_malloc
from batch.utils import batch_log
from config import CHAIN_ID, INDEXER_SYNC_INTERVAL

process_name = "INDEXER-BLOCK_TX_DATA"
LOG = batch_log.get_logger(process_name=process_name)

web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for indexing Block and Transaction data"""

    @staticmethod
    def __get_db_session():
        return BatchAsyncSessionLocal()

    async def process(self):
        local_session = self.__get_db_session()
        try:
            latest_block = await web3.eth.block_number
            from_block = (await self.__get_indexed_block_number(local_session)) + 1

            if from_block > latest_block:
                LOG.info("skip process: from_block > latest_block")
                return

            LOG.info("syncing from={}, to={}".format(from_block, latest_block))
            for block_number in range(from_block, latest_block + 1):
                block_data: BlockData = await web3.eth.get_block(
                    block_number, full_transactions=True
                )

                # Synchronize block data
                block_model = IDXBlockData()
                block_model.number = block_data.get("number")
                block_model.parent_hash = block_data.get("parentHash").to_0x_hex()
                block_model.sha3_uncles = block_data.get("sha3Uncles").to_0x_hex()
                block_model.miner = block_data.get("miner")
                block_model.state_root = block_data.get("stateRoot").to_0x_hex()
                block_model.transactions_root = block_data.get(
                    "transactionsRoot"
                ).to_0x_hex()
                block_model.receipts_root = block_data.get("receiptsRoot").to_0x_hex()
                block_model.logs_bloom = block_data.get("logsBloom").to_0x_hex()
                block_model.difficulty = block_data.get("difficulty")
                block_model.gas_limit = block_data.get("gasLimit")
                block_model.gas_used = block_data.get("gasUsed")
                block_model.timestamp = block_data.get("timestamp")
                block_model.proof_of_authority_data = block_data.get(
                    "proofOfAuthorityData"
                ).to_0x_hex()
                block_model.mix_hash = block_data.get("mixHash").to_0x_hex()
                block_model.nonce = block_data.get("nonce").to_0x_hex()
                block_model.hash = block_data.get("hash").to_0x_hex()
                block_model.size = block_data.get("size")

                transactions: Sequence[TxData] = block_data.get("transactions")
                transaction_hash_list = []
                for transaction in transactions:
                    # Synchronize tx data
                    tx_model = IDXTxData()
                    tx_model.hash = transaction.get("hash").to_0x_hex()
                    tx_model.block_hash = transaction.get("blockHash").to_0x_hex()
                    tx_model.block_number = transaction.get("blockNumber")
                    tx_model.transaction_index = transaction.get("transactionIndex")
                    tx_model.from_address = to_checksum_address(transaction.get("from"))
                    tx_model.to_address = (
                        to_checksum_address(transaction.get("to"))
                        if transaction.get("to")
                        else None
                    )
                    tx_model.input = transaction.get("input").to_0x_hex()
                    tx_model.gas = transaction.get("gas")
                    tx_model.gas_price = transaction.get("gasPrice")
                    tx_model.value = transaction.get("value")
                    tx_model.nonce = transaction.get("nonce")
                    local_session.add(tx_model)

                    transaction_hash_list.append(transaction.get("hash").to_0x_hex())

                block_model.transactions = transaction_hash_list
                local_session.add(block_model)

                await self.__set_indexed_block_number(local_session, block_number)

                await local_session.commit()
        except Exception:
            await local_session.rollback()
            raise
        finally:
            await local_session.close()
        LOG.info("sync process has been completed")

    @staticmethod
    async def __get_indexed_block_number(db_session: AsyncSession):
        indexed_block_number: IDXBlockDataBlockNumber = (
            await db_session.scalars(
                select(IDXBlockDataBlockNumber)
                .where(IDXBlockDataBlockNumber.chain_id == str(CHAIN_ID))
                .limit(1)
            )
        ).first()
        if indexed_block_number is None:
            return -1
        else:
            return indexed_block_number.latest_block_number

    @staticmethod
    async def __set_indexed_block_number(db_session: AsyncSession, block_number: int):
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = str(CHAIN_ID)
        indexed_block_number.latest_block_number = block_number
        await db_session.merge(indexed_block_number)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)
        free_malloc()


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
