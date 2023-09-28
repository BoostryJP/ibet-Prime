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
from typing import Sequence

from sqlalchemy import and_, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.eth import Contract

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import batch_log

from app.exceptions import ServiceUnavailableError
from app.model.db import UTXO, Token, UTXOBlockNumber
from app.utils.contract_utils import ContractUtils
from app.utils.ledger_utils import create_ledger
from app.utils.web3_utils import Web3Wrapper
from config import (
    CREATE_UTXO_BLOCK_LOT_MAX_SIZE,
    CREATE_UTXO_INTERVAL,
    DATABASE_URL,
    ZERO_ADDRESS,
)

"""
[PROCESSOR-Create-UTXO]

Batch processing for creation of ledger data
"""

process_name = "PROCESSOR-Create-UTXO"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

web3 = Web3Wrapper()


class Processor:
    def __init__(self):
        self.token_contract_list = []

    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        latest_synced = True
        try:
            self.__refresh_token_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            utxo_block_number = self.__get_utxo_block_number(db_session=db_session)
            latest_block = web3.eth.block_number

            if utxo_block_number >= latest_block:
                LOG.debug("skip process")
                pass
            else:
                block_from = utxo_block_number + 1
                block_to = latest_block
                if block_to - block_from > CREATE_UTXO_BLOCK_LOT_MAX_SIZE - 1:
                    block_to = block_from + CREATE_UTXO_BLOCK_LOT_MAX_SIZE - 1
                    latest_synced = False
                LOG.info(f"Syncing from={block_from}, to={block_to}")
                for token_contract in self.token_contract_list:
                    event_triggered = False
                    event_triggered = event_triggered | self.__process_transfer(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    event_triggered = event_triggered | self.__process_issue(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    event_triggered = event_triggered | self.__process_redeem(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    event_triggered = event_triggered | self.__process_unlock(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    self.__process_event_triggered(
                        db_session=db_session,
                        token_contract=token_contract,
                        event_triggered=event_triggered,
                    )
                self.__set_utxo_block_number(
                    db_session=db_session, block_number=block_to
                )
                db_session.commit()
        finally:
            db_session.close()
        LOG.info("Sync job has been completed")

        return latest_synced

    def __refresh_token_contract_list(self, db_session: Session):
        self.token_contract_list = []

        # Update token_contract_list to recent
        _token_list: Sequence[Token] = db_session.scalars(
            select(Token).where(Token.token_status == 1).order_by(Token.id)
        ).all()
        for _token in _token_list:
            token_contract = ContractUtils.get_contract(
                contract_name=_token.type, contract_address=_token.token_address
            )
            self.token_contract_list.append(token_contract)

    def __get_utxo_block_number(self, db_session: Session):
        _utxo_block_number = db_session.scalars(
            select(UTXOBlockNumber).limit(1)
        ).first()
        if _utxo_block_number is None:
            return 0
        else:
            return _utxo_block_number.latest_block_number

    def __set_utxo_block_number(self, db_session: Session, block_number: int):
        _utxo_block_number = db_session.scalars(
            select(UTXOBlockNumber).limit(1)
        ).first()
        if _utxo_block_number is None:
            _utxo_block_number = UTXOBlockNumber()
        _utxo_block_number.latest_block_number = block_number
        db_session.merge(_utxo_block_number)

    def __process_transfer(
        self,
        db_session: Session,
        token_contract: Contract,
        block_from: int,
        block_to: int,
    ):
        """Process Transfer Event

        - The process of updating UTXO data by capturing the following events
        - `Transfer` event on Token contracts
        - `HolderChanged` event on Exchange contracts

        :param db_session: database session
        :param token_contract: Token contract
        :param block_from: Block from
        :param block_to: Block to
        :return: Whether events have occurred or not
        """
        try:
            # Get exchange contract address
            exchange_contract_address = ContractUtils.call_function(
                contract=token_contract,
                function_name="tradableExchange",
                args=(),
                default_returns=ZERO_ADDRESS,
            )
            # Get "HolderChanged" events from exchange contract
            exchange_contract = ContractUtils.get_contract(
                contract_name="IbetExchangeInterface",
                contract_address=exchange_contract_address,
            )
            exchange_contract_events = ContractUtils.get_event_logs(
                contract=exchange_contract,
                event="HolderChanged",
                block_from=block_from,
                block_to=block_to,
                argument_filters={"token": token_contract.address},
            )
            tmp_events = []
            for _event in exchange_contract_events:
                if token_contract.address == _event["args"]["token"]:
                    tmp_events.append(
                        {
                            "event": _event["event"],
                            "args": dict(_event["args"]),
                            "transaction_hash": _event["transactionHash"].hex(),
                            "block_number": _event["blockNumber"],
                            "log_index": _event["logIndex"],
                        }
                    )

            # Get "Transfer" events from token contract
            token_transfer_events = ContractUtils.get_event_logs(
                contract=token_contract,
                event="Transfer",
                block_from=block_from,
                block_to=block_to,
            )
            for _event in token_transfer_events:
                tmp_events.append(
                    {
                        "event": _event["event"],
                        "args": dict(_event["args"]),
                        "transaction_hash": _event["transactionHash"].hex(),
                        "block_number": _event["blockNumber"],
                        "log_index": _event["logIndex"],
                    }
                )

            # Marge & Sort: block_number > log_index
            events = sorted(
                tmp_events, key=lambda x: (x["block_number"], x["log_index"])
            )

            # Sink
            event_triggered = False
            for event in events:
                args = event["args"]
                from_account = args.get("from", ZERO_ADDRESS)
                to_account = args.get("to", ZERO_ADDRESS)
                amount = int(args.get("value"))

                # Skip sinking in case of deposit to exchange or withdrawal from exchange
                if (
                    web3.eth.get_code(from_account).hex() != "0x"
                    or web3.eth.get_code(to_account).hex() != "0x"
                ):
                    continue

                transaction_hash = event["transaction_hash"]
                block_number = event["block_number"]
                block_timestamp = datetime.utcfromtimestamp(
                    web3.eth.get_block(block_number)["timestamp"]
                )  # UTC

                if amount is not None and amount <= sys.maxsize:
                    event_triggered = True

                    # Update UTXO（from account）
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=True,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=from_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

                    # Update UTXO（to account）
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=False,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=to_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

            return event_triggered
        except Exception as e:
            LOG.exception(e)
            return False

    def __process_issue(
        self,
        db_session: Session,
        token_contract: Contract,
        block_from: int,
        block_to: int,
    ):
        """Process Issue Event

        - The process of updating UTXO data by capturing the following events
        - `Issue` event on Token contracts

        :param db_session: database session
        :param token_contract: Token contract
        :param block_from: Block from
        :param block_to: Block to
        :return: Whether events have occurred or not
        """
        try:
            # Get "Issue" events from token contract
            events = ContractUtils.get_event_logs(
                contract=token_contract,
                event="Issue",
                block_from=block_from,
                block_to=block_to,
            )

            # Sink
            event_triggered = False
            for event in events:
                args = event["args"]
                account = args.get("targetAddress", ZERO_ADDRESS)
                amount = args.get("amount")

                transaction_hash = event["transactionHash"].hex()
                block_number = event["blockNumber"]
                block_timestamp = datetime.utcfromtimestamp(
                    web3.eth.get_block(block_number)["timestamp"]
                )  # UTC

                if amount is not None and amount <= sys.maxsize:
                    event_triggered = True

                    # Update UTXO
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=False,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

            return event_triggered
        except Exception as e:
            LOG.exception(e)
            return False

    def __process_redeem(
        self,
        db_session: Session,
        token_contract: Contract,
        block_from: int,
        block_to: int,
    ):
        """Process Redeem Event

        - The process of updating UTXO data by capturing the following events
        - `Redeem` event on Token contracts

        :param db_session: database session
        :param token_contract: Token contract
        :param block_from: Block from
        :param block_to: Block to
        :return: Whether events have occurred or not
        """
        try:
            # Get "Redeem" events from token contract
            events = ContractUtils.get_event_logs(
                contract=token_contract,
                event="Redeem",
                block_from=block_from,
                block_to=block_to,
            )

            # Sink
            event_triggered = False
            for event in events:
                args = event["args"]
                account = args.get("targetAddress", ZERO_ADDRESS)
                amount = args.get("amount")

                transaction_hash = event["transactionHash"].hex()
                block_number = event["blockNumber"]
                block_timestamp = datetime.utcfromtimestamp(
                    web3.eth.get_block(block_number)["timestamp"]
                )  # UTC

                if amount is not None and amount <= sys.maxsize:
                    event_triggered = True

                    # Update UTXO
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=True,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

            return event_triggered
        except Exception as e:
            LOG.exception(e)
            return False

    def __process_unlock(
        self,
        db_session: Session,
        token_contract: Contract,
        block_from: int,
        block_to: int,
    ):
        """Process Unlock Event

        - The process of updating UTXO data by capturing the following events
        - `Unlock` event on Token contracts

        :param db_session: database session
        :param token_contract: Token contract
        :param block_from: Block from
        :param block_to: Block to
        :return: Whether events have occurred or not
        """
        try:
            # Get "Unlock" events from token contract
            events = ContractUtils.get_event_logs(
                contract=token_contract,
                event="Unlock",
                block_from=block_from,
                block_to=block_to,
            )

            # Sink
            event_triggered = False
            for event in events:
                args = event["args"]
                from_account = args.get("accountAddress", ZERO_ADDRESS)
                to_account = args.get("recipientAddress", ZERO_ADDRESS)
                amount = args.get("value")

                transaction_hash = event["transactionHash"].hex()
                block_number = event["blockNumber"]
                block_timestamp = datetime.utcfromtimestamp(
                    web3.eth.get_block(block_number)["timestamp"]
                )  # UTC

                if (
                    amount is not None
                    and amount <= sys.maxsize
                    and from_account != to_account
                ):
                    event_triggered = True

                    # Update UTXO（from account）
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=True,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=from_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

                    # Update UTXO（to account）
                    self.__sink_on_utxo(
                        db_session=db_session,
                        spent=False,
                        transaction_hash=transaction_hash,
                        token_address=token_contract.address,
                        account_address=to_account,
                        amount=amount,
                        block_number=block_number,
                        block_timestamp=block_timestamp,
                    )

            return event_triggered
        except Exception as e:
            LOG.exception(e)
            return False

    def __process_event_triggered(
        self, db_session: Session, token_contract: Contract, event_triggered: bool
    ):
        try:
            if event_triggered is True:
                # Create Ledger
                create_ledger(token_address=token_contract.address, db=db_session)
        except Exception as e:
            LOG.exception(e)

    @staticmethod
    def __sink_on_utxo(
        db_session: Session,
        spent: bool,
        transaction_hash: str,
        account_address: str,
        token_address: str,
        amount: int,
        block_number: int,
        block_timestamp: datetime,
    ):
        if not spent:
            _utxo: UTXO | None = db_session.scalars(
                select(UTXO)
                .where(
                    and_(
                        UTXO.transaction_hash == transaction_hash,
                        UTXO.account_address == account_address,
                    )
                )
                .limit(1)
            ).first()
            if _utxo is None:
                _utxo = UTXO()
                _utxo.transaction_hash = transaction_hash
                _utxo.account_address = account_address
                _utxo.token_address = token_address
                _utxo.amount = amount
                _utxo.block_number = block_number
                _utxo.block_timestamp = block_timestamp
                db_session.add(_utxo)
            else:
                utxo_amount = _utxo.amount
                _utxo.amount = utxo_amount + amount
                db_session.merge(_utxo)
        else:
            _utxo_list: Sequence[UTXO] = db_session.scalars(
                select(UTXO)
                .where(
                    and_(
                        UTXO.account_address == account_address,
                        UTXO.token_address == token_address,
                        UTXO.amount > 0,
                    )
                )
                .order_by(UTXO.block_timestamp)
            ).all()
            spend_amount = amount
            for _utxo in _utxo_list:
                utxo_amount = _utxo.amount
                if spend_amount <= 0:
                    break
                elif _utxo.amount <= spend_amount:
                    _utxo.amount = 0
                    spend_amount = spend_amount - utxo_amount
                    db_session.merge(_utxo)
                else:
                    _utxo.amount = utxo_amount - spend_amount
                    spend_amount = 0
                    db_session.merge(_utxo)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        start_time = time.time()
        latest_synced = True
        try:
            latest_synced = processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        if latest_synced is False:
            continue
        else:
            elapsed_time = time.time() - start_time
            time.sleep(max(CREATE_UTXO_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
