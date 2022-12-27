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
from web3.eth import Contract

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from config import (
    INDEXER_SYNC_INTERVAL,
    INDEXER_BLOCK_LOT_MAX_SIZE,
    DATABASE_URL
)
from app.model.db import (
    Token,
    IDXTransfer,
    IDXTransferBlockNumber
)
from app.utils.contract_utils import ContractUtils
from app.utils.web3_utils import Web3Wrapper
from app.exceptions import ServiceUnavailableError
import batch_log

process_name = "INDEXER-Transfer"
LOG = batch_log.get_logger(process_name=process_name)

web3 = Web3Wrapper()

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def __init__(self):
        self.token_list: dict[str, Contract] = {}

    def sync_new_logs(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            self.__get_token_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            latest_block = web3.eth.block_number
            _from_block = self.__get_idx_transfer_block_number(db_session=db_session)
            _to_block = _from_block + INDEXER_BLOCK_LOT_MAX_SIZE

            # Skip processing if the latest block is not counted up
            if _from_block >= latest_block:
                LOG.debug("skip process")
                return

            # Create index data with the upper limit of one process
            # as INDEXER_BLOCK_LOT_MAX_SIZE(1_000_000 blocks)
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=db_session,
                        block_from=_from_block + 1,
                        block_to=_to_block,
                    )
                    _to_block += INDEXER_BLOCK_LOT_MAX_SIZE
                    _from_block += INDEXER_BLOCK_LOT_MAX_SIZE
                self.__sync_all(
                    db_session=db_session,
                    block_from=_from_block + 1,
                    block_to=latest_block
                )
            else:
                self.__sync_all(
                    db_session=db_session,
                    block_from=_from_block + 1,
                    block_to=latest_block
                )

            self.__set_idx_transfer_block_number(
                db_session=db_session,
                block_number=latest_block
            )
            db_session.commit()
        finally:
            db_session.close()
        LOG.info("Sync job has been completed")

    def __get_token_list(self, db_session: Session):
        issued_token_address_list: tuple[str, ...] = tuple(
            [
                record[0] for record in (
                    db_session.query(Token.token_address).filter(Token.token_status == 1).all()
                )
            ]
        )
        loaded_token_address_list: tuple[str, ...] = tuple(self.token_list.keys())
        load_required_address_list = list(set(issued_token_address_list) ^ set(loaded_token_address_list))

        if not load_required_address_list:
            # If there are no additional tokens to load, skip process
            return

        load_required_token_list: list[Token] = (
            db_session.query(Token).
            filter(Token.token_status == 1).
            filter(Token.token_address.in_(load_required_address_list)).all()
        )
        for load_required_token in load_required_token_list:
            token_contract = web3.eth.contract(
                address=load_required_token.token_address,
                abi=load_required_token.abi
            )
            self.token_list[load_required_token.token_address] = token_contract

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
        LOG.info(f"Syncing from={block_from}, to={block_to}")
        self.__sync_transfer(db_session, block_from, block_to)

    def __sync_transfer(self, db_session: Session, block_from: int, block_to: int):
        """Synchronize Transfer events

        :param db_session: database session
        :param block_from: from block number
        :param block_to: to block number
        :return: None
        """
        for token in self.token_list.values():
            try:
                events = ContractUtils.get_event_logs(
                    contract=token,
                    event="Transfer",
                    block_from=block_from,
                    block_to=block_to
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
            except Exception:
                LOG.exception("An exception occurred during event synchronization")

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
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    main()
