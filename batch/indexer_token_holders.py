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
from typing import Dict, Optional, Sequence

import uvloop
from sqlalchemy import and_, create_engine, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from web3.contract import AsyncContract

from app.database import BatchAsyncSessionLocal
from app.exceptions import ServiceUnavailableError
from app.model.blockchain import IbetShareContract, IbetStraightBondContract
from app.model.db import (
    Token,
    TokenHolder,
    TokenHolderBatchStatus,
    TokenHoldersList,
    TokenType,
)
from app.utils.contract_utils import AsyncContractUtils
from app.utils.web3_utils import AsyncWeb3Wrapper
from batch.utils import batch_log
from config import (
    DATABASE_URL,
    INDEXER_BLOCK_LOT_MAX_SIZE,
    INDEXER_SYNC_INTERVAL,
    ZERO_ADDRESS,
)

process_name = "INDEXER-Token-Holders"
LOG = batch_log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

web3 = AsyncWeb3Wrapper()


class Processor:
    """Processor for collecting Token Holders at given block number and token."""

    class BalanceBook:
        pages: Dict[str, TokenHolder]

        def __init__(self):
            self.pages = {}

        def store(self, account_address: str, amount: int = 0, locked: int = 0):
            if account_address not in self.pages:
                token_holder = TokenHolder()
                token_holder.hold_balance = 0 + amount
                token_holder.account_address = account_address
                token_holder.locked_balance = 0 + locked
                self.pages[account_address] = token_holder
            else:
                self.pages[account_address].hold_balance += amount
                self.pages[account_address].locked_balance += locked

    target: Optional[TokenHoldersList]
    balance_book: BalanceBook

    tradable_exchange_address: str
    token_owner_address: str

    token_contract: Optional[AsyncContract]
    exchange_contract: Optional[AsyncContract]
    escrow_contract: Optional[AsyncContract]

    def __init__(self):
        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""

    @staticmethod
    def __get_db_session() -> AsyncSession:
        return BatchAsyncSessionLocal()

    async def __load_target(self, db_session: AsyncSession) -> bool:
        self.target: Optional[TokenHoldersList] = (
            await db_session.scalars(
                select(TokenHoldersList)
                .where(TokenHoldersList.batch_status == TokenHolderBatchStatus.PENDING)
                .limit(1)
            )
        ).first()
        return True if self.target else False

    async def __load_token_info(self, db_session: AsyncSession) -> bool:
        # Fetch token list information from DB
        issued_token: Optional[Token] = (
            await db_session.scalars(
                select(Token)
                .where(
                    and_(
                        Token.token_address == self.target.token_address,
                        Token.token_status == 1,
                    )
                )
                .limit(1)
            )
        ).first()
        if not issued_token:
            return False
        self.token_owner_address = issued_token.issuer_address
        token_type = issued_token.type
        # Store token contract.
        if token_type == TokenType.IBET_STRAIGHT_BOND.value:
            self.token_contract = AsyncContractUtils.get_contract(
                "IbetStraightBond", self.target.token_address
            )
            token_cache = IbetStraightBondContract(self.target.token_address)
            await token_cache.get()
        elif token_type == TokenType.IBET_SHARE.value:
            self.token_contract = AsyncContractUtils.get_contract(
                "IbetShare", self.target.token_address
            )
            token_cache = IbetShareContract(self.target.token_address)
            await token_cache.get()
        else:
            return False

        # Fetch current tradable exchange to store exchange contract.
        self.tradable_exchange_address = token_cache.tradable_exchange_contract_address
        self.exchange_contract = AsyncContractUtils.get_contract(
            contract_name="IbetExchangeInterface",
            contract_address=self.tradable_exchange_address,
        )
        return True

    async def __load_checkpoint(
        self, local_session: AsyncSession, target_token_address: str, block_to: int
    ) -> int:
        _checkpoint: Optional[TokenHoldersList] = (
            await local_session.scalars(
                select(TokenHoldersList)
                .where(
                    and_(
                        TokenHoldersList.token_address == target_token_address,
                        TokenHoldersList.block_number < block_to,
                        TokenHoldersList.batch_status == TokenHolderBatchStatus.DONE,
                    )
                )
                .order_by(TokenHoldersList.block_number.desc())
                .limit(1)
            )
        ).first()
        if _checkpoint:
            _holders: Sequence[TokenHolder] = (
                await local_session.scalars(
                    select(TokenHolder).where(
                        TokenHolder.holder_list_id == _checkpoint.id
                    )
                )
            ).all()
            for holder in _holders:
                self.balance_book.store(
                    account_address=holder.account_address,
                    amount=holder.hold_balance,
                    locked=holder.locked_balance,
                )
            block_from = _checkpoint.block_number + 1
            return block_from
        return 0

    async def collect(self):
        local_session = self.__get_db_session()
        try:
            if not (await self.__load_target(local_session)):
                LOG.debug("There are no pending collect batch")
                return
            if not (await self.__load_token_info(local_session)):
                LOG.debug("Token contract must be listed to TokenList contract.")
                await self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
                await local_session.commit()
                return
            _target_block = self.target.block_number
            _from_block = await self.__load_checkpoint(
                local_session, self.target.token_address, block_to=_target_block
            )
            _to_block = INDEXER_BLOCK_LOT_MAX_SIZE - 1 + _from_block

            if _target_block > _to_block:
                while _to_block < _target_block:
                    await self.__process_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _from_block += INDEXER_BLOCK_LOT_MAX_SIZE
                    _to_block += INDEXER_BLOCK_LOT_MAX_SIZE
                await self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            else:
                await self.__process_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=_target_block,
                )
            await self.__update_status(local_session, TokenHolderBatchStatus.DONE)
            await local_session.commit()
            LOG.info("Collect job has been completed")
        except Exception as e:
            await local_session.rollback()
            await self.__update_status(local_session, TokenHolderBatchStatus.FAILED)
            await local_session.commit()
            raise e
        finally:
            await local_session.close()

    async def __update_status(
        self, local_session: AsyncSession, status: TokenHolderBatchStatus
    ):
        if status == TokenHolderBatchStatus.DONE:
            # Not to store non-holders
            await local_session.execute(
                delete(TokenHolder).where(
                    and_(
                        TokenHolder.holder_list_id == self.target.id,
                        TokenHolder.hold_balance == 0,
                        TokenHolder.locked_balance == 0,
                    )
                )
            )

        self.target.batch_status = status.value
        await local_session.merge(self.target)
        LOG.info(
            f"Token holder list({self.target.list_id}) status changes to be {status.value}."
        )

        self.target = None
        self.balance_book = self.BalanceBook()
        self.tradable_exchange_address = ""
        self.token_owner_address = ""
        self.token_contract = None
        self.exchange_contract = None
        self.escrow_contract = None

    async def __process_all(
        self, db_session: AsyncSession, block_from: int, block_to: int
    ):
        LOG.info("syncing from={}, to={}".format(block_from, block_to))

        await self.__process_transfer(block_from, block_to)
        await self.__process_issue(block_from, block_to)
        await self.__process_redeem(block_from, block_to)
        await self.__process_lock(block_from, block_to)
        await self.__process_unlock(block_from, block_to)

        await self.__save_holders(
            db_session,
            self.balance_book,
            self.target.id,
            self.target.token_address,
            self.token_owner_address,
        )

    async def __process_transfer(self, block_from: int, block_to: int):
        """Process Transfer Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Transfer` event on Token contracts
        - `HolderChanged` event on Exchange contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            tmp_events = []
            # Get "HolderChanged" events from exchange contract
            holder_changed_events = await AsyncContractUtils.get_event_logs(
                contract=self.exchange_contract,
                event="HolderChanged",
                block_from=block_from,
                block_to=block_to,
                argument_filters={"token": self.token_contract.address},
            )
            for _event in holder_changed_events:
                if self.token_contract.address == _event["args"]["token"]:
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
                contract=self.token_contract,
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

            # Marge & Sort: block_number > log_index
            events = sorted(
                tmp_events, key=lambda x: (x["block_number"], x["log_index"])
            )

            for event in events:
                args = event["args"]
                from_account = args.get("from", ZERO_ADDRESS)
                to_account = args.get("to", ZERO_ADDRESS)
                amount = int(args.get("value"))

                # Skip sinking in case of deposit to exchange or withdrawal from exchange
                if (await web3.eth.get_code(from_account)).to_0x_hex() != "0x" or (
                    await web3.eth.get_code(to_account)
                ).to_0x_hex() != "0x":
                    continue

                if amount is not None and amount <= sys.maxsize:
                    # Update Balance（from account）
                    self.balance_book.store(
                        account_address=from_account, amount=-amount
                    )

                    # Update Balance（to account）
                    self.balance_book.store(account_address=to_account, amount=+amount)

        except Exception:
            raise

    async def __process_issue(self, block_from: int, block_to: int):
        """Process Issue Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Issue` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Issue" events from token contract
            events = await AsyncContractUtils.get_event_logs(
                contract=self.token_contract,
                event="Issue",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                args = event["args"]
                account_address = args.get("targetAddress", ZERO_ADDRESS)
                lock_address = args.get("lockAddress", ZERO_ADDRESS)
                amount = args.get("amount")
                if lock_address == ZERO_ADDRESS:
                    if amount is not None and amount <= sys.maxsize:
                        # Update Balance
                        self.balance_book.store(
                            account_address=account_address, amount=+amount
                        )

        except Exception:
            raise

    async def __process_redeem(self, block_from: int, block_to: int):
        """Process Redeem Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Redeem` event on Token contracts

        :param block_from: Block from
        :param block_to: Block to
        :return: None
        """
        try:
            # Get "Redeem" events from token contract
            events = await AsyncContractUtils.get_event_logs(
                contract=self.token_contract,
                event="Redeem",
                block_from=block_from,
                block_to=block_to,
            )

            for event in events:
                args = event["args"]
                account_address = args.get("targetAddress", ZERO_ADDRESS)
                lock_address = args.get("lockAddress", ZERO_ADDRESS)
                amount = args.get("amount")
                if lock_address == ZERO_ADDRESS:
                    if amount is not None and amount <= sys.maxsize:
                        # Update Balance
                        self.balance_book.store(
                            account_address=account_address, amount=-amount
                        )

        except Exception:
            raise

    async def __process_lock(self, block_from: int, block_to: int):
        """Process Lock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Lock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Lock" events from token contract
            events = await AsyncContractUtils.get_event_logs(
                contract=self.token_contract,
                event="Lock",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, amount=-amount, locked=+amount
                    )
        except Exception:
            raise

    async def __process_unlock(self, block_from: int, block_to: int):
        """Process Unlock Event

        - The process of updating Hold-Balance data by capturing the following events
        - `Unlock` event on Token contracts

        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            # Get "Unlock" events from token contract
            events = await AsyncContractUtils.get_event_logs(
                contract=self.token_contract,
                event="Unlock",
                block_from=block_from,
                block_to=block_to,
            )
            for event in events:
                args = event["args"]
                account_address = args.get("accountAddress", ZERO_ADDRESS)
                recipient_address = args.get("recipientAddress", ZERO_ADDRESS)
                amount = args.get("value")
                if amount is not None and amount <= sys.maxsize:
                    self.balance_book.store(
                        account_address=account_address, locked=-amount
                    )
                    self.balance_book.store(
                        account_address=recipient_address, amount=+amount
                    )
        except Exception:
            raise

    @staticmethod
    async def __save_holders(
        db_session: AsyncSession,
        balance_book: BalanceBook,
        holder_list_id: int,
        token_address: str,
        token_owner_address: str,
    ):
        for account_address, page in zip(
            balance_book.pages.keys(), balance_book.pages.values()
        ):
            if page.account_address == token_owner_address:
                # Skip storing data for token owner
                continue
            token_holder: TokenHolder | None = (
                await db_session.scalars(
                    select(TokenHolder)
                    .where(
                        and_(
                            TokenHolder.holder_list_id == holder_list_id,
                            TokenHolder.account_address == account_address,
                        )
                    )
                    .limit(1)
                )
            ).first()
            if token_holder is not None:
                token_holder.hold_balance = page.hold_balance
                token_holder.locked_balance = page.locked_balance
                await db_session.merge(token_holder)
            elif page.hold_balance > 0 or page.locked_balance > 0:
                LOG.debug(
                    f"Collection record created : token_address={token_address}, account_address={account_address}"
                )
                page.holder_list_id = holder_list_id
                db_session.add(page)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            await processor.collect()
        except ServiceUnavailableError:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        await asyncio.sleep(INDEXER_SYNC_INTERVAL)


if __name__ == "__main__":
    try:
        uvloop.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
