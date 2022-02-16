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
from eth_utils import to_checksum_address
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    INDEXER_SYNC_INTERVAL,
    DATABASE_URL
)
from app.model.db import (
    Token,
    IDXTransfer,
    IDXTransferBlockNumber
)
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log

process_name = "INDEXER-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self):
        self.latest_block = web3.eth.blockNumber
        self.token_list = []

    def sync_new_logs(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            self.__get_token_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            idx_transfer_block_number = self.__get_idx_transfer_block_number(db_session=db_session)
            latest_block = web3.eth.blockNumber

            if idx_transfer_block_number >= latest_block:
                LOG.debug("skip process")
                pass
            else:
                self.__sync_all(
                    db_session=db_session,
                    block_from=idx_transfer_block_number + 1,
                    block_to=latest_block
                )
                self.__set_idx_transfer_block_number(
                    db_session=db_session,
                    block_number=latest_block
                )
                db_session.commit()
        finally:
            db_session.close()

    def __get_token_list(self, db_session: Session):
        self.token_list = []
        issued_token_list = db_session.query(Token).filter(Token.token_status == 1).all()
        for issued_token in issued_token_list:
            token_contract = web3.eth.contract(
                address=issued_token.token_address,
                abi=issued_token.abi
            )
            self.token_list.append(token_contract)

    def __get_idx_transfer_block_number(self, db_session: Session):
        _idx_transfer_block_number = db_session.query(IDXTransferBlockNumber). \
            first()
        if _idx_transfer_block_number is None:
            return 0
        else:
            return _idx_transfer_block_number.latest_block_number

    def __set_idx_transfer_block_number(self, db_session: Session, block_number: int):
        _idx_transfer_block_number = db_session.query(IDXTransferBlockNumber). \
            first()
        if _idx_transfer_block_number is None:
            _idx_transfer_block_number = IDXTransferBlockNumber()

        _idx_transfer_block_number.latest_block_number = block_number
        db_session.merge(_idx_transfer_block_number)

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info(f"syncing from={block_from}, to={block_to}")
        self.__sync_transfer(db_session, block_from, block_to)

    def __sync_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Transfer events

        :param db_session: database session
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
                    args = event["args"]
                    transaction_hash = event["transactionHash"].hex()
                    block_timestamp = datetime.utcfromtimestamp(web3.eth.get_block(event["blockNumber"])["timestamp"])
                    if args["value"] > sys.maxsize:
                        pass
                    else:
                        self.__sink_on_transfer(
                            db_session=db_session,
                            transaction_hash=transaction_hash,
                            token_address=to_checksum_address(token.address),
                            from_address=args["from"],
                            to_address=args["to"],
                            amount=args["value"],
                            block_timestamp=block_timestamp
                        )
            except Exception as e:
                LOG.error(e)

    @staticmethod
    def __sink_on_transfer(db_session: Session,
                           transaction_hash: str,
                           token_address: str,
                           from_address: str,
                           to_address: str,
                           amount: int,
                           block_timestamp: datetime):
        transfer_record = IDXTransfer()
        transfer_record.transaction_hash = transaction_hash
        transfer_record.token_address = token_address
        transfer_record.from_address = from_address
        transfer_record.to_address = to_address
        transfer_record.amount = amount
        transfer_record.block_timestamp = block_timestamp
        db_session.add(transfer_record)
        LOG.debug(f"Transfer: transaction_hash={transaction_hash}")


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.sync_new_logs()
            LOG.debug("Processed")
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
