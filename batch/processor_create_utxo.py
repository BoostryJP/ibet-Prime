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
import time
from datetime import UTC, datetime
from typing import Sequence

import uvloop
from sqlalchemy import and_, create_engine, select
from sqlalchemy.exc import DataError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import UTXO, Account, Token, TokenType, UTXOBlockNumber
from app.utils.contract_utils import AsyncContractEventsView, AsyncContractUtils
from app.utils.ledger_utils import request_ledger_creation
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch.utils import batch_log
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

web3 = AsyncWeb3Wrapper()


class Processor:
    def __init__(self):
        self.token_contract_list: list[AsyncContractEventsView] = []
        self.token_type_map: dict[str, TokenType] = {}

    async def process(self):
        db_session: AsyncSession = BatchAsyncSessionLocal()
        latest_synced = True
        try:
            await self.__refresh_token_contract_list(db_session=db_session)

            # Get from_block_number and to_block_number for contract event filter
            utxo_block_number = await self.__get_utxo_block_number(
                db_session=db_session
            )
            latest_block = await web3.eth.block_number

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
                    event_triggered = event_triggered | await self.__process_issue(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    event_triggered = event_triggered | await self.__process_transfer(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    event_triggered = event_triggered | await self.__process_redeem(
                        db_session=db_session,
                        token_contract=token_contract,
                        block_from=block_from,
                        block_to=block_to,
                    )
                    if event_triggered is True:
                        # If an event is triggered, initiate the ledger creation request.
                        try:
                            async with db_session.begin_nested():
                                await request_ledger_creation(
                                    db=db_session, token_address=token_contract.address
                                )
                                await db_session.flush()
                        except DataError:
                            LOG.error(
                                f"Invalid record detected. Ledger creation request has been discarded and not saved: token_address={token_contract.address}"
                            )
                await self.__set_utxo_block_number(
                    db_session=db_session, block_number=block_to
                )
                await db_session.commit()
        finally:
            await db_session.close()

        LOG.info("Sync job has been completed")

        return latest_synced

    async def __refresh_token_contract_list(self, db_session: AsyncSession):
        self.token_contract_list = []

        # Update token_contract_list to recent
        _token_list: Sequence[Token] = (
            await db_session.scalars(
                select(Token)
                .join(
                    Account,
                    and_(
                        Account.issuer_address == Token.issuer_address,
                        Account.is_deleted == False,
                    ),
                )
                .where(Token.token_status == 1)
                .order_by(Token.id)
            )
        ).all()
        for _token in _token_list:
            token_contract = AsyncContractUtils.get_contract(
                contract_name=_token.type, contract_address=_token.token_address
            )
            self.token_contract_list.append(
                AsyncContractEventsView(
                    token_contract.address,
                    token_contract.events,
                )
            )
            self.token_type_map[_token.token_address] = _token.type

    @staticmethod
    async def __get_utxo_block_number(db_session: AsyncSession):
        _utxo_block_number = (
            await db_session.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        if _utxo_block_number is None:
            return 0
        else:
            return _utxo_block_number.latest_block_number

    @staticmethod
    async def __set_utxo_block_number(db_session: AsyncSession, block_number: int):
        _utxo_block_number = (
            await db_session.scalars(select(UTXOBlockNumber).limit(1))
        ).first()
        if _utxo_block_number is None:
            _utxo_block_number = UTXOBlockNumber()
        _utxo_block_number.latest_block_number = block_number
        await db_session.merge(_utxo_block_number)

    async def __process_transfer(
        self,
        db_session: AsyncSession,
        token_contract: AsyncContractEventsView,
        block_from: int,
        block_to: int,
    ):
        """Process Transfer Event

        - The process of updating UTXO data by capturing the following events
        - `Transfer` event on Token contracts
        - `Unlock` event on Token contracts
        - `HolderChanged` event on Exchange contracts

        :param db_session: database session
        :param token_contract: Token contract
        :param block_from: Block from
        :param block_to: Block to
        :return: Whether events have occurred or not
        """
        # Get exchange contract address
        exchange_contract_address = ZERO_ADDRESS
        if (
            self.token_type_map.get(token_contract.address)
            == TokenType.IBET_STRAIGHT_BOND.value
        ):
            bond_token = IbetStraightBondContract(token_contract.address)
            await bond_token.get()
            exchange_contract_address = bond_token.tradable_exchange_contract_address
        elif (
            self.token_type_map.get(token_contract.address)
            == TokenType.IBET_SHARE.value
        ):
            share_token = IbetShareContract(token_contract.address)
            await share_token.get()
            exchange_contract_address = share_token.tradable_exchange_contract_address

        # Get "HolderChanged" events from exchange contract
        exchange_contract = AsyncContractUtils.get_contract(
            contract_name="IbetExchangeInterface",
            contract_address=exchange_contract_address,
        )
        exchange_contract_events = await AsyncContractUtils.get_event_logs(
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
                        "transaction_hash": _event["transactionHash"].to_0x_hex(),
                        "block_number": _event["blockNumber"],
                        "log_index": _event["logIndex"],
                    }
                )

        # Get "Transfer" events from token contract
        token_transfer_events = await AsyncContractUtils.get_event_logs(
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
                    "transaction_hash": _event["transactionHash"].to_0x_hex(),
                    "block_number": _event["blockNumber"],
                    "log_index": _event["logIndex"],
                }
            )

        # Get "Unlock" events from token contract
        token_unlock_events = await AsyncContractUtils.get_event_logs(
            contract=token_contract,
            event="Unlock",
            block_from=block_from,
            block_to=block_to,
        )
        for _event in token_unlock_events:
            if _event["args"]["accountAddress"] != _event["args"]["recipientAddress"]:
                tmp_events.append(
                    {
                        "event": _event["event"],
                        "args": dict(_event["args"]),
                        "transaction_hash": _event["transactionHash"].to_0x_hex(),
                        "block_number": _event["blockNumber"],
                        "log_index": _event["logIndex"],
                    }
                )

        # Marge & Sort: block_number > log_index
        events = sorted(tmp_events, key=lambda x: (x["block_number"], x["log_index"]))

        # Sink
        event_triggered = False
        for event in events:
            args = event["args"]
            if event["event"] == "Unlock":
                from_account = args.get("accountAddress", ZERO_ADDRESS)
                to_account = args.get("recipientAddress", ZERO_ADDRESS)
                amount = args.get("value")
            else:
                from_account = args.get("from", ZERO_ADDRESS)
                to_account = args.get("to", ZERO_ADDRESS)
                amount = int(args.get("value"))

            # Skip sinking in case of deposit to exchange or withdrawal from exchange
            if (await web3.eth.get_code(from_account)).to_0x_hex() != "0x" or (
                await web3.eth.get_code(to_account)
            ).to_0x_hex() != "0x":
                continue

            transaction_hash = event["transaction_hash"]
            block_number = event["block_number"]
            block_timestamp = datetime.fromtimestamp(
                (await web3.eth.get_block(block_number))["timestamp"], UTC
            ).replace(tzinfo=None)  # UTC

            if amount is not None and amount <= sys.maxsize:
                event_triggered = True

                # Update UTXO（from account）
                await self.__sink_on_utxo(
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
                await self.__sink_on_utxo(
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

    async def __process_issue(
        self,
        db_session: AsyncSession,
        token_contract: AsyncContractEventsView,
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
        # Get "Issue" events from token contract
        events = await AsyncContractUtils.get_event_logs(
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

            transaction_hash = event["transactionHash"].to_0x_hex()
            block_number = event["blockNumber"]
            block_timestamp = datetime.fromtimestamp(
                (await web3.eth.get_block(block_number))["timestamp"], UTC
            ).replace(tzinfo=None)  # UTC

            if amount is not None and amount <= sys.maxsize:
                event_triggered = True

                # Update UTXO
                await self.__sink_on_utxo(
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

    async def __process_redeem(
        self,
        db_session: AsyncSession,
        token_contract: AsyncContractEventsView,
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
        # Get "Redeem" events from token contract
        events = await AsyncContractUtils.get_event_logs(
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

            transaction_hash = event["transactionHash"].to_0x_hex()
            block_number = event["blockNumber"]
            block_timestamp = datetime.fromtimestamp(
                (await web3.eth.get_block(block_number))["timestamp"], UTC
            ).replace(tzinfo=None)  # UTC

            if amount is not None and amount <= sys.maxsize:
                event_triggered = True

                # Update UTXO
                await self.__sink_on_utxo(
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

    @staticmethod
    async def __sink_on_utxo(
        db_session: AsyncSession,
        spent: bool,
        transaction_hash: str,
        account_address: str,
        token_address: str,
        amount: int,
        block_number: int,
        block_timestamp: datetime,
    ):
        if not spent:
            _utxo: UTXO | None = (
                await db_session.scalars(
                    select(UTXO)
                    .where(
                        and_(
                            UTXO.transaction_hash == transaction_hash,
                            UTXO.account_address == account_address,
                        )
                    )
                    .limit(1)
                )
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
                await db_session.merge(_utxo)
        else:
            _utxo_list: Sequence[UTXO] = (
                await db_session.scalars(
                    select(UTXO)
                    .where(
                        and_(
                            UTXO.account_address == account_address,
                            UTXO.token_address == token_address,
                            UTXO.amount > 0,
                        )
                    )
                    .order_by(UTXO.block_timestamp)
                )
            ).all()
            spend_amount = amount
            for _utxo in _utxo_list:
                utxo_amount = _utxo.amount
                if spend_amount <= 0:
                    break
                elif _utxo.amount <= spend_amount:
                    _utxo.amount = 0
                    spend_amount = spend_amount - utxo_amount
                    await db_session.merge(_utxo)
                else:
                    _utxo.amount = utxo_amount - spend_amount
                    spend_amount = 0
                    await db_session.merge(_utxo)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        start_time = time.time()
        latest_synced = True
        try:
            latest_synced = await processor.process()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An error occurred during processing")

        if latest_synced is False:
            continue
        else:
            elapsed_time = time.time() - start_time
            await asyncio.sleep(max(CREATE_UTXO_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
